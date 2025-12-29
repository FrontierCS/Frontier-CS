#include <bits/stdc++.h>
using namespace std;

struct custom_hash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return splitmix64(x + FIXED_RANDOM);
    }
};

static long long walk_cmd(long long x) {
    cout << "walk " << x << '\n' << flush;
    long long v;
    if (!(cin >> v)) exit(0);
    if (v == -1) exit(0);
    return v;
}

static void guess_cmd(long long g) {
    cout << "guess " << g << '\n' << flush;
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int M = 100000;

    unordered_map<long long, int, custom_hash> first_time;
    first_time.reserve((size_t)M * 2);
    first_time.max_load_factor(0.7f);

    long long total = 0;
    long long start = walk_cmd(0);
    first_time[start] = 0;

    long long cur = start;

    // Record labels at times 0..M-1
    for (int i = 1; i < M; i++) {
        cur = walk_cmd(1);
        ++total;
        auto it = first_time.find(cur);
        if (it != first_time.end()) {
            guess_cmd(total - it->second);
        }
        first_time[cur] = (int)total;
    }

    // Move to time M (multiple of M) without recording
    cur = walk_cmd(1);
    ++total;
    if (cur == start) guess_cmd(total);

    // Giant steps of size M until collision with recorded prefix
    while (true) {
        cur = walk_cmd(M);
        total += M;
        auto it = first_time.find(cur);
        if (it != first_time.end()) {
            guess_cmd(total - it->second);
        }
    }
    return 0;
}