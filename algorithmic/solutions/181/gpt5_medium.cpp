#include <bits/stdc++.h>
using namespace std;

static const uint64_t START_TIME = chrono::duration_cast<chrono::milliseconds>(
    chrono::steady_clock::now().time_since_epoch()).count();

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline bool skip() {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }
    inline bool nextInt(int &out) {
        if (!skip()) return false;
        char c = read();
        int sgn = 1;
        if (c == '-') { sgn = -1; c = read(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        out = x * sgn;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) return 0;

    const int N = n;
    vector<uint8_t> D((size_t)N * N);
    vector<int> degD_out(N, 0), degD_in(N, 0);

    for (int i = 0; i < N; ++i) {
        int base = i * N;
        for (int j = 0; j < N; ++j) {
            int v; fs.nextInt(v);
            D[base + j] = (uint8_t)v;
            degD_out[i] += v;
            degD_in[j] += v;
        }
    }

    vector<uint8_t> Fmat((size_t)N * N);
    vector<vector<int>> outF(N), inF(N);
    long long totalFlow = 0;
    for (int i = 0; i < N; ++i) {
        int base = i * N;
        for (int j = 0; j < N; ++j) {
            int v; fs.nextInt(v);
            Fmat[base + j] = (uint8_t)v;
            if (v) {
                outF[i].push_back(j);
                inF[j].push_back(i);
                totalFlow++;
            }
        }
    }

    vector<int> degF_tot(N, 0), degF_out(N, 0), degF_in(N, 0);
    for (int i = 0; i < N; ++i) {
        degF_out[i] = (int)outF[i].size();
        degF_in[i] = (int)inF[i].size();
        degF_tot[i] = degF_out[i] + degF_in[i];
    }
    vector<int> degD_tot(N, 0), degD_out_copy = degD_out;
    for (int i = 0; i < N; ++i) {
        degD_tot[i] = degD_out[i] + degD_in[i];
    }

    vector<int> fac(N), locAsc(N), locDesc(N);
    iota(fac.begin(), fac.end(), 0);
    sort(fac.begin(), fac.end(), [&](int a, int b){
        if (degF_tot[a] != degF_tot[b]) return degF_tot[a] > degF_tot[b];
        if (degF_out[a] != degF_out[b]) return degF_out[a] > degF_out[b];
        return a < b;
    });
    iota(locAsc.begin(), locAsc.end(), 0);
    sort(locAsc.begin(), locAsc.end(), [&](int a, int b){
        if (degD_tot[a] != degD_tot[b]) return degD_tot[a] < degD_tot[b];
        if (degD_out[a] != degD_out[b]) return degD_out[a] < degD_out[b];
        return a < b;
    });
    iota(locDesc.begin(), locDesc.end(), 0);
    sort(locDesc.begin(), locDesc.end(), [&](int a, int b){
        if (degD_tot[a] != degD_tot[b]) return degD_tot[a] > degD_tot[b];
        if (degD_out[a] != degD_out[b]) return degD_out[a] > degD_out[b];
        return a < b;
    });

    auto calc_cost = [&](const vector<int>& p)->long long{
        long long cost = 0;
        for (int i = 0; i < N; ++i) {
            int pi = p[i] * N;
            const vector<int>& outs = outF[i];
            for (int j : outs) {
                cost += D[pi + p[j]];
            }
        }
        return cost;
    };

    vector<int> p1(N, 0), p2(N, 0);
    for (int i = 0; i < N; ++i) p1[fac[i]] = locAsc[i];
    for (int i = 0; i < N; ++i) p2[fac[i]] = locDesc[i];

    long long cost1 = calc_cost(p1);
    long long cost2 = calc_cost(p2);

    vector<int> p = (cost1 <= cost2) ? p1 : p2;
    long long cost = min(cost1, cost2);

    // Prepare for local improvement
    vector<int> heavy = fac; // already sorted by degF_tot desc
    int K = min(N, 200);
    heavy.resize(K);

    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> distN(0, N - 1);

    auto now_ms = []()->uint64_t{
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now().time_since_epoch()).count();
    };
    uint64_t time_start = now_ms();
    uint64_t TIME_LIMIT_MS = 1800; // heuristic time budget

    auto delta_swap = [&](int a, int b)->long long {
        if (a == b) return 0;
        int x = p[a], y = p[b];
        const uint8_t *Dx = &D[(size_t)x * N];
        const uint8_t *Dy = &D[(size_t)y * N];
        long long delta = 0;

        // Out neighbors of a
        const auto &oa = outF[a];
        for (int i : oa) {
            if (i == a || i == b) continue;
            int pi = p[i];
            delta += (long long)Dy[pi] - (long long)Dx[pi];
        }
        // In neighbors of a
        const auto &ia = inF[a];
        for (int i : ia) {
            if (i == a || i == b) continue;
            int pi = p[i];
            delta += (long long)D[(size_t)pi * N + y] - (long long)D[(size_t)pi * N + x];
        }
        // Out neighbors of b
        const auto &ob = outF[b];
        for (int i : ob) {
            if (i == a || i == b) continue;
            int pi = p[i];
            delta += (long long)Dx[pi] - (long long)Dy[pi];
        }
        // In neighbors of b
        const auto &ib = inF[b];
        for (int i : ib) {
            if (i == a || i == b) continue;
            int pi = p[i];
            delta += (long long)D[(size_t)pi * N + x] - (long long)D[(size_t)pi * N + y];
        }

        // Corrections for (a,a), (b,b), (a,b), (b,a)
        delta += (long long)Fmat[(size_t)a * N + a] * ((long long)D[(size_t)y * N + y] - (long long)D[(size_t)x * N + x]);
        delta += (long long)Fmat[(size_t)b * N + b] * ((long long)D[(size_t)x * N + x] - (long long)D[(size_t)y * N + y]);
        delta += (long long)Fmat[(size_t)a * N + b] * ((long long)D[(size_t)y * N + x] - (long long)D[(size_t)x * N + y]);
        delta += (long long)Fmat[(size_t)b * N + a] * ((long long)D[(size_t)x * N + y] - (long long)D[(size_t)y * N + x]);

        return delta;
    };

    // Local improvement loop
    int M = min(N - 1, 64);
    int no_improve_loops = 0;
    while (now_ms() - time_start < TIME_LIMIT_MS) {
        bool improved_round = false;
        for (int idx = 0; idx < K; ++idx) {
            if (now_ms() - time_start >= TIME_LIMIT_MS) break;
            int a = heavy[idx];
            long long bestDelta = 0;
            int bestB = -1;
            for (int t = 0; t < M; ++t) {
                int b = distN(rng);
                if (b == a) { if (++b >= N) b = 0; if (b == a) continue; }
                long long d = delta_swap(a, b);
                if (d < bestDelta) {
                    bestDelta = d;
                    bestB = b;
                }
            }
            if (bestB != -1) {
                cost += bestDelta;
                swap(p[a], p[bestB]);
                improved_round = true;
            }
        }
        if (!improved_round) {
            no_improve_loops++;
            if (no_improve_loops >= 2) break;
        } else {
            no_improve_loops = 0;
        }
    }

    // Output permutation 1-indexed
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}