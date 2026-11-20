#define _GNU_SOURCE
#include <cairo/cairo.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <sys/resource.h>
#include <sys/signalfd.h>
#include <unistd.h>
#include <wayland-client.h>
#include <linux/input-event-codes.h>
#include <xkbcommon/xkbcommon.h>
#include "xdg-shell-client.h"

extern uint8_t seed_generate(uint8_t, size_t, const uint8_t *, size_t, uint16_t *);
extern const char *seed_word(uint16_t);
extern size_t seed_word_len(uint16_t);

enum { WIDTH = 820, HEIGHT = 570, STRIDE = WIDTH * 4, FRAME = STRIDE * HEIGHT };
enum page { LENGTH, METHOD, ENTROPY, PHRASE, CHECK_SIZE, CHECK, COMPLETE, LOCK_ERROR };
struct frame { uint8_t *pixels; struct wl_buffer *object; bool busy; };
static struct {
    enum page page;
    size_t count, used, check_count, check_index;
    unsigned method;
    uint16_t words[24];
    uint8_t positions[24];
    unsigned char input[1024];
    const char *notice;
} flow;
static struct frame frames[2];
static struct wl_display *display;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct wl_surface *surface;
static struct wl_seat *seat;
static struct wl_keyboard *keyboard;
static struct wl_pointer *pointer;
static struct wl_buffer *cursor_buffer;
enum { CURSOR_SIZE = 20 };
static struct wl_surface *cursor_surface;
static struct xdg_toplevel *top;
static int pointer_x, pointer_y;
enum { TITLE_HEIGHT = 40, CLOSE_WIDTH = 48 };
static struct xdg_wm_base *shell;
static struct xkb_context *keys;
static struct xkb_state *key_state;
static bool running = true, configured, dirty = true, failed;

static void clear_input(void) {
    explicit_bzero(flow.input, sizeof(flow.input));
    flow.used = 0;
}

static void clear_words(void) {
    explicit_bzero(flow.words, sizeof(flow.words));
    clear_input();
}

static void change(enum page page) {
    clear_input();
    flow.notice = NULL;
    flow.page = page;
    dirty = true;
}

static bool prepare_check(size_t count) {
    for (size_t i = 0; i < flow.count; i++) flow.positions[i] = i;
    /* Unbiased partial Fisher-Yates. Linux randomness selects positions only. */
    for (size_t i = 0; count != flow.count && i < count; i++) {
        unsigned remaining = flow.count - i;
        unsigned limit = 256 - 256 % remaining;
        uint8_t random;
        do {
            if (getrandom(&random, 1, 0) != 1) return false;
        } while (random >= limit);
        size_t j = i + random % remaining;
        uint8_t first = flow.positions[i];
        flow.positions[i] = flow.positions[j];
        flow.positions[j] = first;
    }
    flow.check_count = count;
    flow.check_index = 0;
    change(CHECK);
    return true;
}

static void submit(void) {
    switch (flow.page) {
    case LENGTH:
        if (flow.used == 2 && memcmp(flow.input, "12", 2) == 0) flow.count = 12;
        else if (flow.used == 2 && memcmp(flow.input, "24", 2) == 0) flow.count = 24;
        else { flow.notice = "Enter 12 or 24."; break; }
        change(METHOD);
        return;
    case METHOD:
        if (flow.used != 1 || flow.input[0] < '1' || flow.input[0] > '4') {
            flow.notice = "Choose 1, 2, 3 or 4.";
            break;
        }
        flow.method = flow.input[0] - '0';
        change(ENTROPY);
        return;
    case ENTROPY: {
        uint8_t result = seed_generate(flow.method, flow.count, flow.input, flow.used, flow.words);
        if (!result) { change(PHRASE); return; }
        static const char *messages[] = {
            "", "Check the characters and count, then try again.",
            "More rolls are needed. Keep rolling, then press Enter.",
            "Remove the rolls after you reached the required bit count.",
            "Too much of the draw repeats. Start with a fresh draw."
        };
        flow.notice = messages[result];
        if (result == 4) clear_input();
        return;
    }
    case PHRASE:
        change(CHECK_SIZE);
        return;
    case CHECK_SIZE: {
        unsigned count = 0;
        bool all = flow.used == 1 && (flow.input[0] == 'a' || flow.input[0] == 'A');
        if (all) count = flow.count;
        else if (flow.used && flow.used <= 2) {
            for (size_t i = 0; i < flow.used; i++) {
                if (flow.input[i] < '0' || flow.input[i] > '9') { count = 0; break; }
                count = count * 10 + flow.input[i] - '0';
            }
        }
        if (count < 4 || (!all && count > 12)) {
            flow.notice = "Enter A for every word, or a number from 4 to 12.";
            break;
        }
        if (prepare_check(count)) return;
        clear_words();
        change(LOCK_ERROR);
        flow.notice = "Could not choose random check positions. The phrase was cleared.";
        return;
    }
    case CHECK: {
        unsigned index = flow.words[flow.positions[flow.check_index]];
        bool match = flow.used == seed_word_len(index) &&
                     memcmp(flow.input, seed_word(index), flow.used) == 0;
        if (!match) {
            flow.notice = "That word did not match. Check your backup and try again.";
            break;
        }
        if (++flow.check_index == flow.check_count) {
            clear_words();
            change(COMPLETE);
            return;
        }
        change(CHECK);
        return;
    }
    case COMPLETE:
    case LOCK_ERROR:
        running = false;
        return;
    }
    clear_input();
}

static void text(cairo_t *cr, int x, int y, int size, const char *line) {
    cairo_set_font_size(cr, size);
    cairo_move_to(cr, x, y);
    cairo_show_text(cr, line);
}

static void release(void *data, struct wl_buffer *unused) {
    (void)unused;
    struct frame *f = data;
    explicit_bzero(f->pixels, FRAME);
    f->busy = false;
}
static const struct wl_buffer_listener buffer_listener = { release };

static void paint(void) {
    struct frame *f = !frames[0].busy ? frames : !frames[1].busy ? frames + 1 : NULL;
    if (!dirty || !configured || !f) return;
    cairo_surface_t *canvas = cairo_image_surface_create_for_data(
        f->pixels, CAIRO_FORMAT_RGB24, WIDTH, HEIGHT, STRIDE);
    cairo_t *cr = cairo_create(canvas);
    if (cairo_status(cr) != CAIRO_STATUS_SUCCESS) {
        cairo_destroy(cr);
        cairo_surface_destroy(canvas);
        failed = true;
        running = false;
        return;
    }
    cairo_set_source_rgb(cr, .035, .061, .10);
    cairo_paint(cr);
    cairo_select_font_face(cr, "sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_source_rgb(cr, .10, .16, .22);
    cairo_rectangle(cr, 0, 0, WIDTH, TITLE_HEIGHT);
    cairo_fill(cr);
    cairo_set_source_rgb(cr, .79, .85, .91);
    text(cr, 16, 26, 16, "Refugium Seed Creator   v" SEED_VERSION);
    int center = WIDTH - CLOSE_WIDTH / 2;
    cairo_set_line_width(cr, 2);
    cairo_move_to(cr, center - 6, 14);
    cairo_line_to(cr, center + 6, 26);
    cairo_move_to(cr, center + 6, 14);
    cairo_line_to(cr, center - 6, 26);
    cairo_stroke(cr);
    cairo_set_source_rgb(cr, .60, .83, .98);
    text(cr, 42, 90, 30, "Create a seed phrase");
    cairo_set_source_rgb(cr, .91, .95, 1);
    char line[128];
    switch (flow.page) {
    case LENGTH:
        text(cr, 42, 135, 21, "Would you like a 12 or 24 word seed phrase?");
        text(cr, 42, 180, 18, "Have paper ready to record your words in private.");
        break;
    case METHOD:
        text(cr, 42, 135, 21, "Choose how to draw your own entropy");
        text(cr, 42, 186, 20, "1   Dice, hand-checkable");
        text(cr, 42, 226, 20, "2   Dice, hashed");
        text(cr, 42, 266, 20, "3   Coin flips");
        text(cr, 42, 306, 20, "4   Entropia pills and coin flips");
        break;
    case ENTROPY:
        if (flow.method == 1) {
            snprintf(line, sizeof(line), "Type fair die rolls until you have %zu bits.", flow.count * 32 / 3);
            text(cr, 42, 135, 21, line);
            text(cr, 42, 176, 18, "1 = 00   2 = 01   3 = 10   4 = 11   5 = 0   6 = 1");
            size_t bits = 0;
            for (size_t i = 0; i < flow.used; i++) {
                unsigned c = flow.input[i];
                if (c >= '1' && c <= '6') bits += c <= '4' ? 2 : 1;
            }
            snprintf(line, sizeof(line), "%zu of %zu bits%s", bits, flow.count * 32 / 3,
                     bits >= flow.count * 32 / 3 ? "   •   Stop rolling" : "");
            text(cr, 42, 228, 21, line);
        } else if (flow.method == 2) {
            snprintf(line, sizeof(line), "Type at least %u fair die rolls (digits 1–6).", flow.count == 12 ? 50 : 100);
            text(cr, 42, 135, 21, line);
        } else if (flow.method == 3) {
            snprintf(line, sizeof(line), "Type %zu fair coin flips using H and T or 1 and 0.", flow.count * 32 / 3);
            text(cr, 42, 135, 21, line);
        } else {
            text(cr, 42, 135, 21, flow.count == 12 ?
                "Type 7 coin flips, then 11 freshly drawn pill words." :
                "Type 7 coin flips, 22 freshly drawn pill words, then 7 more flips.");
            text(cr, 42, 176, 18, "Use H/T or 1/0. Separate the groups and each word with spaces.");
            text(cr, 42, 212, 18, "Draw each word independently. Return the pills between draws.");
        }
        text(cr, 42, 290, 18, "Your input is hidden.");
        break;
    case PHRASE:
        text(cr, 42, 121, 19, "Write the words down in this order. Enter hides them for the check.");
        for (size_t i = 0; i < flow.count; i++) {
            int x = 42 + (i / 8) * 253;
            int y = 165 + (i % 8) * 36;
            unsigned index = flow.words[i];
            snprintf(line, sizeof(line), "%2zu   %.*s", i + 1, (int)seed_word_len(index), seed_word(index));
            text(cr, x, y, 22, line);
            explicit_bzero(line, sizeof(line));
        }
        break;
    case CHECK_SIZE:
        text(cr, 42, 135, 21, "How many words do you want to check?");
        text(cr, 42, 180, 18, "Type A for every word, or choose 4 to 12 random positions.");
        break;
    case CHECK:
        snprintf(line, sizeof(line), "Check %zu of %zu   •   Enter word %u from your backup",
                 flow.check_index + 1, flow.check_count, flow.positions[flow.check_index] + 1);
        text(cr, 42, 135, 21, line);
        break;
    case COMPLETE:
        text(cr, 42, 135, 21, "Backup check passed.");
        text(cr, 42, 180, 18, "The utility cleared its seed and input buffers.");
        break;
    case LOCK_ERROR:
        text(cr, 42, 135, 21, "Seed creation stopped.");
        break;
    }
    if (flow.page != PHRASE && flow.page != COMPLETE && flow.page != LOCK_ERROR) {
        if (flow.page == ENTROPY || flow.page == CHECK) {
            snprintf(line, sizeof(line), "%zu characters entered", flow.used);
        } else {
            snprintf(line, sizeof(line), "Choice: %.*s", (int)flow.used, flow.input);
        }
        cairo_set_source_rgb(cr, .10, .16, .22);
        cairo_rectangle(cr, 32, 373, WIDTH - 64, 52);
        cairo_fill(cr);
        cairo_set_source_rgb(cr, .91, .95, 1);
        text(cr, 48, 405, 20, line);
    }
    cairo_set_source_rgb(cr, 1, .72, .47);
    if (flow.notice) text(cr, 42, 461, 18, flow.notice);
    cairo_set_source_rgb(cr, .65, .73, .83);
    text(cr, 42, 520, 17, flow.page == LENGTH ?
        "Type 12 or 24, then press Enter   •   Esc to close" :
        flow.page == CHECK ?
        "Enter to check   •   F2 to show the phrase again   •   Esc to close and clear" :
        "Enter to continue   •   Esc to close and clear");
    cairo_destroy(cr);
    cairo_surface_destroy(canvas);
    f->busy = true;
    dirty = false;
    wl_surface_attach(surface, f->object, 0, 0);
    wl_surface_damage(surface, 0, 0, WIDTH, HEIGHT);
    wl_surface_commit(surface);
}

static void on_keymap(void *unused, struct wl_keyboard *kb, uint32_t format, int fd, uint32_t size) {
    (void)unused; (void)kb;
    if (format == WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1 && size) {
        char *data = mmap(NULL, size, PROT_READ, MAP_PRIVATE, fd, 0);
        if (data != MAP_FAILED) {
            struct xkb_keymap *map = xkb_keymap_new_from_buffer(keys, data, size - 1,
                XKB_KEYMAP_FORMAT_TEXT_V1, XKB_KEYMAP_COMPILE_NO_FLAGS);
            if (map) {
                xkb_state_unref(key_state);
                key_state = xkb_state_new(map);
                xkb_keymap_unref(map);
            }
            munmap(data, size);
        }
    }
    close(fd);
}

static void on_enter(void *d, struct wl_keyboard *k, uint32_t serial, struct wl_surface *s, struct wl_array *a)
{ (void)d; (void)k; (void)serial; (void)s; (void)a; }
static void on_leave(void *d, struct wl_keyboard *k, uint32_t serial, struct wl_surface *s)
{ (void)d; (void)k; (void)serial; (void)s; }
static void on_repeat(void *d, struct wl_keyboard *k, int32_t rate, int32_t delay)
{ (void)d; (void)k; (void)rate; (void)delay; }

static void on_key(void *d, struct wl_keyboard *kb, uint32_t serial, uint32_t time, uint32_t key, uint32_t state) {
    (void)d; (void)kb; (void)serial; (void)time;
    if (!key_state || state != WL_KEYBOARD_KEY_STATE_PRESSED) return;
    xkb_keysym_t sym = xkb_state_key_get_one_sym(key_state, key + 8);
    if (sym == XKB_KEY_Escape) { running = false; return; }
    if (sym == XKB_KEY_F2 && flow.page == CHECK) {
        change(PHRASE);
    } else if (sym == XKB_KEY_Return || sym == XKB_KEY_KP_Enter) {
        submit();
    } else if (sym == XKB_KEY_BackSpace && flow.used) {
        flow.input[--flow.used] = 0;
        flow.notice = NULL;
    } else if (flow.page != LOCK_ERROR && flow.page != PHRASE && flow.page != COMPLETE) {
        unsigned c = xkb_state_key_get_utf32(key_state, key + 8);
        bool secret_entry = flow.page == ENTROPY || flow.page == CHECK;
        bool menu_key = (c >= '0' && c <= '9') ||
                        (flow.page == CHECK_SIZE && (c == 'a' || c == 'A'));
        if ((menu_key || (secret_entry && c >= ' ' && c <= '~')) &&
            flow.used < sizeof(flow.input)) {
            flow.input[flow.used++] = c;
            flow.notice = NULL;
        }
    }
    dirty = true;
}
static void on_mods(void *d, struct wl_keyboard *kb, uint32_t serial,
                    uint32_t depressed, uint32_t latched, uint32_t locked, uint32_t group) {
    (void)d; (void)kb; (void)serial;
    if (key_state) xkb_state_update_mask(key_state, depressed, latched, locked, 0, 0, group);
}
static const struct wl_keyboard_listener keyboard_listener = {
    on_keymap, on_enter, on_leave, on_key, on_mods, on_repeat
};
static void motion(void *d, struct wl_pointer *p, uint32_t time, wl_fixed_t x, wl_fixed_t y) {
    (void)d; (void)p; (void)time;
    pointer_x = wl_fixed_to_int(x);
    pointer_y = wl_fixed_to_int(y);
}
static void pointer_enter(void *d, struct wl_pointer *p, uint32_t serial,
                          struct wl_surface *s, wl_fixed_t x, wl_fixed_t y) {
    (void)s;
    motion(d, p, 0, x, y);
    if (!cursor_surface || !cursor_buffer) return;
    wl_pointer_set_cursor(p, serial, cursor_surface, 0, 0);
    wl_surface_attach(cursor_surface, cursor_buffer, 0, 0);
    wl_surface_damage(cursor_surface, 0, 0, CURSOR_SIZE, CURSOR_SIZE);
    wl_surface_commit(cursor_surface);
}
static void pointer_leave(void *d, struct wl_pointer *p, uint32_t serial, struct wl_surface *s)
{ (void)d; (void)p; (void)serial; (void)s; }
static void axis(void *d, struct wl_pointer *p, uint32_t t, uint32_t a, wl_fixed_t v)
{ (void)d; (void)p; (void)t; (void)a; (void)v; }
static void button(void *d, struct wl_pointer *p, uint32_t serial, uint32_t time,
                   uint32_t code, uint32_t state) {
    (void)d; (void)p; (void)time;
    if (code != BTN_LEFT || state != WL_POINTER_BUTTON_STATE_PRESSED ||
        pointer_y < 0 || pointer_y >= TITLE_HEIGHT || !top) return;
    if (pointer_x >= WIDTH - CLOSE_WIDTH) running = false;
    else xdg_toplevel_move(top, seat, serial);
}
static const struct wl_pointer_listener pointer_listener = {
    .enter = pointer_enter, .leave = pointer_leave, .motion = motion, .button = button, .axis = axis
};
static void capabilities(void *d, struct wl_seat *s, uint32_t caps) {
    (void)d;
    if ((caps & WL_SEAT_CAPABILITY_POINTER) && !pointer) {
        pointer = wl_seat_get_pointer(s);
        wl_pointer_add_listener(pointer, &pointer_listener, NULL);
    } else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && pointer) {
        wl_pointer_destroy(pointer);
        pointer = NULL;
    }
    if (caps & WL_SEAT_CAPABILITY_KEYBOARD) {
        if (!keyboard) {
            keyboard = wl_seat_get_keyboard(s);
            wl_keyboard_add_listener(keyboard, &keyboard_listener, NULL);
        }
    } else if (keyboard) {
        wl_keyboard_destroy(keyboard);
        keyboard = NULL;
    }
}
static void seat_name(void *d, struct wl_seat *s, const char *name)
{ (void)d; (void)s; (void)name; }
static const struct wl_seat_listener seat_listener = { capabilities, seat_name };

static void ping(void *d, struct xdg_wm_base *s, uint32_t serial)
{ (void)d; xdg_wm_base_pong(s, serial); }
static const struct xdg_wm_base_listener shell_listener = { ping };
static void global(void *d, struct wl_registry *r, uint32_t name, const char *interface, uint32_t version) {
    (void)d;
    if (!strcmp(interface, wl_compositor_interface.name))
        compositor = wl_registry_bind(r, name, &wl_compositor_interface, 1);
    else if (!strcmp(interface, wl_shm_interface.name))
        shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
    else if (!strcmp(interface, wl_seat_interface.name) && version >= 1 && !seat) {
        seat = wl_registry_bind(r, name, &wl_seat_interface, 1);
        wl_seat_add_listener(seat, &seat_listener, NULL);
    } else if (!strcmp(interface, xdg_wm_base_interface.name)) {
        shell = wl_registry_bind(r, name, &xdg_wm_base_interface, 1);
        xdg_wm_base_add_listener(shell, &shell_listener, NULL);
    }
}
static void remove_global(void *d, struct wl_registry *r, uint32_t name)
{ (void)d; (void)r; (void)name; }
static const struct wl_registry_listener registry_listener = { global, remove_global };
static void config(void *d, struct xdg_surface *s, uint32_t serial)
{ (void)d; xdg_surface_ack_configure(s, serial); configured = true; dirty = true; }
static const struct xdg_surface_listener surface_listener = { config };
static void size_change(void *d, struct xdg_toplevel *t, int32_t w, int32_t h, struct wl_array *s)
{ (void)d; (void)t; (void)w; (void)h; (void)s; }
static void close_window(void *d, struct xdg_toplevel *t)
{ (void)d; (void)t; running = false; }
static const struct xdg_toplevel_listener toplevel_listener = {
    .configure = size_change, .close = close_window
};

static bool buffers(void) {
    int fd = memfd_create("refugium-display", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (fd < 0) return false;
    int size = 2 * FRAME + CURSOR_SIZE * CURSOR_SIZE * 4;
    if (ftruncate(fd, size) != 0) { close(fd); return false; }
    void *map = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (map == MAP_FAILED) { close(fd); return false; }
    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
    for (unsigned i = 0; i < 2; i++) {
        frames[i].pixels = (uint8_t *)map + i * FRAME;
        frames[i].object = wl_shm_pool_create_buffer(pool, i * FRAME, WIDTH, HEIGHT, STRIDE, WL_SHM_FORMAT_XRGB8888);
        wl_buffer_add_listener(frames[i].object, &buffer_listener, &frames[i]);
    }
    /* A small static pointer keeps the window independent of cursor theme allocations. */
    uint32_t *pixels = (uint32_t *)((uint8_t *)map + 2 * FRAME);
    for (int y = 0; y < CURSOR_SIZE; y++) {
        int edge = y < 14 ? y * 2 / 3 : CURSOR_SIZE - y;
        for (int x = 0; x <= edge; x++) {
            pixels[y * CURSOR_SIZE + x] = (x == 0 || x == edge) ? 0xff101820 : 0xffffffff;
        }
    }
    cursor_buffer = wl_shm_pool_create_buffer(pool, 2 * FRAME, CURSOR_SIZE, CURSOR_SIZE,
                                              CURSOR_SIZE * 4, WL_SHM_FORMAT_ARGB8888);
    wl_shm_pool_destroy(pool);
    close(fd);
    return true;
}

int main(void) {
    sigset_t signals;
    sigemptyset(&signals);
    sigaddset(&signals, SIGHUP); sigaddset(&signals, SIGINT);
    sigaddset(&signals, SIGTERM); sigaddset(&signals, SIGQUIT);
    struct rlimit zero = {0, 0};
    if (sigprocmask(SIG_BLOCK, &signals, NULL) || setrlimit(RLIMIT_CORE, &zero) ||
        prctl(PR_SET_DUMPABLE, 0L, 0L, 0L, 0L)) return 1;
    int signal_fd = signalfd(-1, &signals, SFD_CLOEXEC);
    if (signal_fd < 0) return 1;
    bool locked = mlockall(MCL_CURRENT | MCL_FUTURE) == 0;
    if (!locked) {
        flow.page = LOCK_ERROR;
        flow.notice = "Could not lock memory. No seed was generated.";
    }
    display = wl_display_connect(NULL);
    if (!display) return 1;
    struct wl_registry *registry = wl_display_get_registry(display);
    keys = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    if (!keys || wl_registry_add_listener(registry, &registry_listener, NULL) ||
        wl_display_roundtrip(display) < 0 || !shm || !shell || !compositor || !seat || !buffers()) {
        return 1;
    }
    surface = wl_compositor_create_surface(compositor);
    struct xdg_surface *xdg = xdg_wm_base_get_xdg_surface(shell, surface);
    cursor_surface = wl_compositor_create_surface(compositor);
    top = xdg_surface_get_toplevel(xdg);
    xdg_surface_add_listener(xdg, &surface_listener, NULL);
    xdg_toplevel_add_listener(top, &toplevel_listener, NULL);
    xdg_toplevel_set_title(top, "Refugium Seed Creator");
    xdg_toplevel_set_app_id(top, "refugium-seed");
    xdg_toplevel_set_min_size(top, WIDTH, HEIGHT);
    xdg_toplevel_set_max_size(top, WIDTH, HEIGHT);
    wl_surface_commit(surface);
    while (running) {
        if (wl_display_dispatch_pending(display) < 0 || !running) break;
        paint();
        if (!running) break;
        short events = POLLIN;
        if (wl_display_flush(display) < 0) {
            if (errno != EAGAIN) break;
            events |= POLLOUT;
        }
        struct pollfd fds[] = {{wl_display_get_fd(display), events, 0}, {signal_fd, POLLIN, 0}};
        int ready = poll(fds, 2, -1);
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0 || fds[1].revents || fds[0].revents & (POLLHUP | POLLERR | POLLNVAL)) break;
        if (fds[0].revents & POLLIN && wl_display_dispatch(display) < 0) break;
    }
    clear_words();
    explicit_bzero(frames[0].pixels, 2 * FRAME);
    xdg_toplevel_destroy(top);
    xdg_surface_destroy(xdg);
    wl_surface_destroy(surface);
    wl_display_flush(display);
    wl_display_disconnect(display);
    return !locked || failed;
}
