#include <gtk/gtk.h>

static void copy_line(GtkButton *button, gpointer data) {
    GtkTextBuffer *buffer = GTK_TEXT_BUFFER(data);
    GtkTextIter start, end;
    gtk_text_buffer_get_iter_at_mark(buffer, &start, gtk_text_buffer_get_insert(buffer));
    gtk_text_iter_set_line_offset(&start, 0);
    end = start;
    if (gtk_text_iter_ends_line(&end)) {
        gtk_button_set_label(button, "Choose a nonempty line");
        return;
    }
    gtk_text_iter_forward_to_line_end(&end);
    gchar *text = gtk_text_buffer_get_text(buffer, &start, &end, FALSE);
    GtkClipboard *clipboard = gtk_widget_get_clipboard(GTK_WIDGET(button), GDK_SELECTION_CLIPBOARD);
    gtk_clipboard_set_text(clipboard, text, -1);
    gtk_text_buffer_select_range(buffer, &start, &end);
    gtk_button_set_label(button, "Line copied");
    g_free(text);
}

static void reset_label(GtkTextBuffer *buffer, GParamSpec *spec, gpointer button) {
    (void)buffer;
    (void)spec;
    gtk_button_set_label(GTK_BUTTON(button), "Copy line");
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    gchar *contents = NULL;
    gsize size = 0;
    if (!g_file_get_contents("/home/live/pubkeys", &contents, &size, NULL) ||
        size > G_MAXINT || !g_utf8_validate(contents, size, NULL))
        return 1;

    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "Public keys for testing");
    gtk_window_set_default_size(GTK_WINDOW(window), 870, 560);
    g_signal_connect(window, "destroy", G_CALLBACK(gtk_main_quit), NULL);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(box), 12);
    gtk_container_add(GTK_CONTAINER(window), box);
    GtkWidget *instructions = gtk_label_new("Click a line and choose Copy line, or select text and press Ctrl+C.");
    gtk_widget_set_halign(instructions, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(box), instructions, FALSE, FALSE, 0);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_box_pack_start(GTK_BOX(box), scroll, TRUE, TRUE, 0);
    GtkWidget *text = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(text), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(text), TRUE);
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(text), GTK_WRAP_WORD_CHAR);
    gtk_container_add(GTK_CONTAINER(scroll), text);
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(text));
    gtk_text_buffer_set_text(buffer, contents, (gint)size);
    g_free(contents);
    GtkTextIter start;
    gtk_text_buffer_get_start_iter(buffer, &start);
    gtk_text_buffer_place_cursor(buffer, &start);
    GtkWidget *copy = gtk_button_new_with_label("Copy line");
    gtk_widget_set_halign(copy, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(box), copy, FALSE, FALSE, 0);
    g_signal_connect(copy, "clicked", G_CALLBACK(copy_line), buffer);
    g_signal_connect(buffer, "notify::cursor-position", G_CALLBACK(reset_label), copy);
    gtk_widget_show_all(window);
    gtk_widget_grab_focus(text);
    gtk_main();
    return 0;
}
