#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <sys/wait.h>
#include <unistd.h>

static void fail(const char *label) {
    dprintf(1, "W3-PROBE FAIL %s errno=%d\n", label, errno);
    sync();
    reboot(RB_POWER_OFF);
    _exit(1);
}
static int read_counter(const char *wanted) {
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    int value = -1;
    char row[256], key[64]; int n;
    while (fgets(row, sizeof row, f))
        if (sscanf(row, "%63s %d", key, &n) == 2 && strcmp(key, wanted) == 0) { value=n; break; }
    fclose(f);
    return value;
}
static int present(const char *folder, const char *property) {
    DIR *dir = opendir(folder);
    if (!dir) return -1;
    int count = 0;
    struct dirent *e;
    while ((e = readdir(dir))) {
        if (e->d_name[0] == '.') continue;
        char p[512], value[128];
        snprintf(p, sizeof p, "%s/%s/class", folder, e->d_name);
        FILE *f = fopen(p,"r");
        if (!f) continue;
        if (fgets(value,sizeof value,f) && strncmp(value,property,strlen(property)) == 0) {
            snprintf(p,sizeof p,"%s/%s/driver",folder,e->d_name);
            char driver[512];
            ssize_t size=readlink(p,driver,sizeof driver-1);
            if(size>=0) {
                driver[size]=0;
                printf("W3-PROBE transport_or_driver=%s\n",strrchr(driver,'/')?strrchr(driver,'/')+1:driver);
                if(!strstr(driver,"/virtio-pci")) { fclose(f); closedir(dir); return -1; }
            }
            count++;
        }
        fclose(f);
    }
    closedir(dir);
    return count;
}
int main(void) {
    if (mount("proc","/proc","proc",0,0) || mount("sysfs","/sys","sysfs",0,0)) fail("mount proc and sysfs");
    DIR *net = opendir("/sys/class/net"); if (!net) fail("net access");
    int lo=0; struct dirent *e;
    while ((e=readdir(net))) {
        if (e->d_name[0]=='.') continue;
        if (strcmp(e->d_name,"lo")) fail("unexpected network device");
        lo++;
    }
    closedir(net); if(lo!=1) fail("loopback missing");
    if(access("/proc/swaps",F_OK)==0 || errno!=ENOENT) fail("swap present");
    if(access("/proc/modules",F_OK)==0 || errno!=ENOENT) fail("modules present");
    DIR *virt=opendir("/sys/bus/virtio/devices");
    if (!virt) fail("virtio bus not present");
    int virt_net=0;
    while ((e=readdir(virt))) {
        if(e->d_name[0]=='.') continue;
        char path[512], id[64];
        snprintf(path,sizeof path,"/sys/bus/virtio/devices/%s/device",e->d_name);
        FILE *fp=fopen(path,"r");
        if(fp && fgets(id,sizeof id,fp) && strtol(id,0,0)==1) {
            virt_net++;
            snprintf(path,sizeof path,"/sys/bus/virtio/devices/%s/driver",e->d_name);
            if(access(path,F_OK)==0) fail("virtio network driver bound");
        }
        if(fp) fclose(fp);
    }
    closedir(virt); if(virt_net!=1) fail("virtio NIC function not enumerated");
    int n=present("/sys/bus/pci/devices","0x0200"); if(n<2) fail("presented NIC count or binding");
    printf("W3-PROBE net=lo pci_ethernet_without_network_driver=%d proc_swaps=absent proc_modules=absent\n",n);
    fflush(stdout);
    struct rlimit limit={67108864,67108864};
    if(setrlimit(RLIMIT_MEMLOCK,&limit)) fail("session limit");
    pid_t pid=fork(); if(pid<0) fail("fork");
    if(pid==0) {
        if(setgid(65534)||setuid(65534)) _exit(2);
        if(mlockall(MCL_CURRENT|MCL_FUTURE)) _exit(3);
        int before=read_counter("VmLck:");
        void *p=mmap(NULL,1048576,PROT_READ|PROT_WRITE,MAP_ANONYMOUS|MAP_PRIVATE,-1,0);
        if(p==MAP_FAILED) _exit(4);
        memset(p,0xa5,1048576);
        int after=read_counter("VmLck:");
        if(before<=0 || after<before+1024) _exit(5);
        printf("W3-PROBE unprivileged_memlock_bytes=67108864 locked_before_KiB=%d locked_after_KiB=%d\n",before,after);
        fflush(stdout);
        _exit(0);
    }
    int status;
    if(waitpid(pid,&status,0)!=pid || !WIFEXITED(status) || WEXITSTATUS(status)!=0) fail("whole-process lock probe");
    puts("W3-PROBE PASS"); fflush(stdout); sync(); reboot(RB_POWER_OFF); return 0;
}
