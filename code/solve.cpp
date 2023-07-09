// c++ -std=c++20 -O2 -o solve solve.cpp
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <unistd.h>


using std::chrono::steady_clock;


typedef uint8_t u8;
typedef uint32_t u32;
typedef int32_t i32;
typedef int64_t i64;
typedef float r32;
typedef double r64;


typedef struct __attribute__((packed)) {
    u32 room_w, room_h;
    u32 stage_w, stage_h;
    u32 stage_x, stage_y;
    u32 instruments, musicians;
    u32 attendees;
    u32 pillars;
    u32 scoring_mode;
    u32 time_limit;
} pack_header;


typedef struct __attribute__((packed)) {
    r32 x, y;
} pack_pos;


typedef struct __attribute__((packed)) {
    i32 x, y;
} pack_ipos;


typedef struct __attribute__((packed)) {
    i32 x, y, r;
} pack_pillar;


static inline u8
timed_out(const steady_clock::time_point& time_start, u32 time_limit) {
    if (time_limit != 0) {
        auto now = steady_clock::now();
        std::chrono::duration<r32> elapsed = now - time_start;
        if (elapsed.count() >= time_limit) {
            return 1;
        }
    }
    return 0;
}


static i64
score_placement(u32 pos_index, u32 instrument, const pack_pos* ans, const pack_header& conf, const u32* musicians, const pack_ipos* people,
    const i32* tastes, const pack_pillar* pillars) {
    i64 score = 0;
    for (u32 i = 0; i < conf.attendees; ++i) {
        r64 dx = ans[pos_index].x - people[i].x;
        r64 dy = ans[pos_index].y - people[i].y;
        r64 d2 = dx * dx + dy * dy;
        u8 reaching = 1;
        for (u32 z = 0; z < conf.musicians; ++z) {
            if (z != pos_index) {
                r64 dzx = people[i].x - ans[z].x;
                r64 dzy = people[i].y - ans[z].y;
                r64 dt = (dx * dzy - dzx * dy);
                if (dt * dt / d2 < 25) {
                    if (dzx * dzx + dzy * dzy < d2) {
                        reaching = 0;
                        break;
                    }
                }
            }
        }
        
        for (u32 z = 0; z < conf.pillars; ++z) {
            r64 r = pillars[z].r;
            r64 dzx = people[i].x - pillars[z].x;
            r64 dzy = people[i].y - pillars[z].y;
            r64 dt = (dx * dzy - dzx * dy);
            if (dt * dt / d2 < r * r) {
                if (dzx * dzx + dzy * dzy < d2) {
                    reaching = 0;
                    break;
                }
            }
        }
        
        if (reaching) {
            score += ceil(r64(1000000) * tastes[conf.instruments * i + instrument] / d2);
        }
    }
    if (conf.scoring_mode == 2) {
        r64 qlick = 1;
        for (u32 z = 0; z < conf.musicians; ++z) {
            if (instrument == musicians[z] && z != pos_index) {
                r64 dx = ans[pos_index].x - ans[z].x;
                r64 dy = ans[pos_index].y - ans[z].y;
                qlick += 1 / sqrt(dx * dx + dy * dy);
            }
        }
        score = ceil(score * qlick);
    }
    return score;
}


static i64
solve(const pack_header& conf, const u32* musicians, const pack_ipos* people,
    const i32* tastes, const pack_pillar* pillars, pack_pos* ans, u32* ans_vol) {
    auto ts_start = steady_clock::now();
    const r32 R = 10, R2 = 20;
    const r32 R34h = 15;

#if 0
    // square packing
    r32 y = R;
    r32 x = R;
    for (u32 i = 0; i < conf.musicians; ++i) {
        ans[i].x = x + conf.stage_x;
        ans[i].y = y + conf.stage_y;
        x += R2;
        if (x >= conf.stage_w - R) {
            x = R;
            y += R2;
        }
    }
#endif

#if 0
    // hex packing
    r32 y = R;
    r32 x = R;
    u32 run = 0;
    for (u32 i = 0; i < conf.musicians; ++i) {
        ans[i].x = x + conf.stage_x;
        ans[i].y = y + conf.stage_y;
        x += R2;
        if (x >= conf.stage_w - R) {
            ++run;
            x = (run % 2) * R + R;
            y += R34h;
        }
    }
#endif
    
#if 1
    // hex grid
    const u32 MAXG = conf.stage_w * conf.stage_h / R2;
    pack_pos grid[MAXG];
    u32 ig = 0;
    u32 run = 0;
    for (u32 y = R; y <= conf.stage_h - R; y += R34h, ++run) {
        for (u32 x = (run % 2) * R + R; x <= conf.stage_w - R; x += R2) {
            u8 valid = 1;
#if 0
            for (u32 z = 0; z < conf.pillars; ++z) {
                r32 dx = r32(x) + conf.stage_x - pillars[z].x;
                r32 dy = r32(y) + conf.stage_y - pillars[z].y;
                r32 r = pillars[z].r;
                if (dx*dx + dy*dy < r*r) {
                    valid = 0;
                    break;
                }
            }
#endif
            if (valid) {
                grid[ig].x = x + conf.stage_x;
                grid[ig].y = y + conf.stage_y;
                ++ig;
                if (ig >= MAXG) { break; }
            }
        }
    }
    if (ig < conf.musicians) {
        fprintf(stderr, "! maxg:%u, ig:%u, musicians:%u\n", MAXG, ig, conf.musicians);
    }

    std::random_device rng; rng();
    std::default_random_engine rgen(rng());
    std::uniform_int_distribution<u32> dist(0, ig-1);
    u8 seen[ig];
    memset(&seen[0], 0, ig);
    for (u32 i = 0; i < conf.musicians; ++i) {
        u32 j = dist(rgen);
        if (seen[j]) {
            j = dist(rgen);
        }
        if (seen[j]) {
            for (u32 k = 0; k < ig; ++k) {
                if (!seen[k]) {
                    seen[k] = 1;
                    ans[i] = grid[k];
                    break;
                }
            }            
        }
        else {
            seen[j] = 1;
            ans[i] = grid[j];
        }
    }
#endif
    
    i64 score = 0;
    for (u32 j = 0; j < conf.musicians; ++j) {
        score += score_placement(j, musicians[j], ans, conf, musicians, people, tastes, pillars);
    }

#if 1
    // random swaps
    for (u32 k = 0; k < conf.musicians; ++k) {
        i64 k0 = score_placement(k, musicians[k], ans, conf, musicians, people, tastes, pillars);
        for (u32 j = conf.musicians - 1; j > k; --j) {
            if (musicians[k] == musicians[j]) { continue; }
            i64 j0 = score_placement(j, musicians[j], ans, conf, musicians, people, tastes, pillars);
            i64 k1 = score_placement(j, musicians[k], ans, conf, musicians, people, tastes, pillars);
            i64 j1 = score_placement(k, musicians[j], ans, conf, musicians, people, tastes, pillars);
            if (k0 + j0 < k1 + j1) {
                pack_pos t = ans[k];
                ans[k] = ans[j];
                ans[j] = t;
                score -= k0 + j0;
                score += k1 + j1;
                k0 = k1;
            }
        }
        if (timed_out(ts_start, conf.time_limit)) {
            break;
        }
    }
#endif

    score = 0;
    for (u32 k = 0; k < conf.musicians; ++k) {
        i64 s = score_placement(k, musicians[k], ans, conf, musicians, people, tastes, pillars);
        u32 vol = s > 0 ? 10 : 1;
        ans_vol[k] = vol;
        score += s * vol;
    }

    return score;
}


static int
readin(void* buf, size_t size) {
    size_t total = 0;
    for (; total < size; ) {
        size_t n = read(STDIN_FILENO, buf, size);
        if (n == -1) {
            perror("read failed");
            exit(1);
        }
        total += n;
    }
    return total;
}


int
main(int argc, char* argv[]) {
    u8* msg_pack = nullptr;
    
    if (argc > 1) {
        FILE* fp = fopen(argv[1], "rb");
        if (!fp) {
            perror(argv[1]);
            return 1;
        }
        fseek(fp, 0, SEEK_END);
        size_t sz = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        msg_pack = (u8*) malloc(sz);
        fread(msg_pack, 1, sz, fp);
        fclose(fp);
    }

    if (!msg_pack) {
        u32 msg_size = 0;
        u32 res = readin(&msg_size, sizeof(msg_size));
        if (i32(res) <= 0) {
            puts("! missing input");
            return 1;
        }

        msg_pack = (u8*) malloc(msg_size);
        readin(msg_pack, msg_size);
    }

    size_t off = 0;
    pack_header conf = *(pack_header*) &msg_pack[off];
    off += sizeof(pack_header);
    
    u32* musicians = (u32*) &msg_pack[off];
    off += conf.musicians * sizeof(u32);

    pack_ipos* ppl = (pack_ipos*) &msg_pack[off];
    off += conf.attendees * sizeof(pack_ipos);

    i32* tastes = (i32*) &msg_pack[off];
    off += conf.attendees * conf.instruments * sizeof(i32);

    pack_pillar* pillars = (pack_pillar*) &msg_pack[off];
    off += conf.pillars * sizeof(pack_pillar);

    
    pack_pos* ans = (pack_pos*) malloc(conf.musicians * sizeof(pack_pos));
    u32* vol = (u32*) malloc(conf.musicians * sizeof(u32));
    
    i64 score = solve(conf, musicians, ppl, tastes, pillars, &ans[0], &vol[0]);

    write(STDOUT_FILENO, &score, sizeof(score));
    write(STDOUT_FILENO, &conf.musicians, sizeof(conf.musicians));
    write(STDOUT_FILENO, &ans[0], conf.musicians * sizeof(pack_pos));
    write(STDOUT_FILENO, &conf.musicians, sizeof(conf.musicians));
    write(STDOUT_FILENO, &vol[0], conf.musicians * sizeof(u32));
    
    return 0;
}
