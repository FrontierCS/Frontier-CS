#include <bits/stdc++.h>
using namespace std;

struct XorShift {
    uint64_t x;
    XorShift(uint64_t seed = 88172645463393265ULL) { x = seed; }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t next_uint(uint32_t mod) { return (uint32_t)(next() % mod); }
    inline double next_double() { return (next() & ((1ULL<<53)-1)) * (1.0 / (double)(1ULL<<53)); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    const int H = 50, W = 50, N = H * W;
    vector<int> t(N), p(N);
    int maxT = -1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            int x; cin >> x;
            t[i*W + j] = x;
            if (x > maxT) maxT = x;
        }
    }
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            int x; cin >> x;
            p[i*W + j] = x;
        }
    }
    int M = maxT + 1;

    // Precompute adjacency to different tiles
    vector<array<int,4>> neigh(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            int v = i*W + j;
            int d = 0;
            if (i > 0) {
                int u = (i-1)*W + j;
                if (t[u] != t[v]) neigh[v][d++] = u;
            }
            if (i+1 < H) {
                int u = (i+1)*W + j;
                if (t[u] != t[v]) neigh[v][d++] = u;
            }
            if (j > 0) {
                int u = i*W + (j-1);
                if (t[u] != t[v]) neigh[v][d++] = u;
            }
            if (j+1 < W) {
                int u = i*W + (j+1);
                if (t[u] != t[v]) neigh[v][d++] = u;
            }
            deg[v] = d;
            for (int k = d; k < 4; ++k) neigh[v][k] = -1;
        }
    }

    auto dirChar = [&](int from, int to)->char{
        if (to == from - W) return 'U';
        if (to == from + W) return 'D';
        if (to == from - 1) return 'L';
        return 'R';
    };

    // Versioned visited tiles
    vector<int> visited_ver(M, -1);
    int cur_ver = 0;

    auto attempt = [&](double a, double b, double pen0, double pen1, double noiseAmp, double eps, XorShift &rng, string &out_moves, int &out_score) {
        int start = si*W + sj;
        cur_ver++;
        int ver = cur_ver;
        visited_ver[t[start]] = ver;

        int cur = start;
        int score = p[cur];
        string moves;
        moves.reserve(3000);

        while (true) {
            // enumerate candidates
            int best_to = -1;
            double best_sc = -1e100;

            int cand_idx[4];
            int cc = 0;
            for (int k = 0; k < deg[cur]; ++k) {
                int nb = neigh[cur][k];
                if (nb < 0) continue;
                if (visited_ver[t[nb]] == ver) continue;
                cand_idx[cc++] = nb;
            }
            if (cc == 0) break;

            // epsilon-greedy
            bool random_choice = (rng.next_double() < eps);

            for (int ci = 0; ci < cc; ++ci) {
                int nb = cand_idx[ci];
                if (random_choice) {
                    double val = rng.next_double();
                    if (val > best_sc) { best_sc = val; best_to = nb; }
                    continue;
                }
                // Evaluate
                int degAfter = 0;
                int maxNextP = 0;
                // count next options and best next p
                for (int k = 0; k < deg[nb]; ++k) {
                    int nxt = neigh[nb][k];
                    if (nxt < 0) continue;
                    if (visited_ver[t[nxt]] == ver) continue;
                    degAfter++;
                    if (p[nxt] > maxNextP) maxNextP = p[nxt];
                }

                double sc = (double)p[nb] + a * (double)maxNextP + b * (double)degAfter;
                if (degAfter == 0) sc -= pen0;
                else if (degAfter == 1) sc -= pen1;
                sc += (rng.next_double()*2.0 - 1.0) * noiseAmp;

                if (sc > best_sc) {
                    best_sc = sc;
                    best_to = nb;
                }
            }

            int nxt = best_to;
            if (nxt == -1) break;

            visited_ver[t[nxt]] = ver;
            moves.push_back(dirChar(cur, nxt));
            score += p[nxt];
            cur = nxt;
        }

        out_moves = moves;
        out_score = score;
    };

    XorShift rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Time limit
    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.9; // seconds

    string best_moves;
    int best_score = -1;

    // Try a deterministic baseline first (greedy with degree bias)
    {
        string mv; int sc;
        attempt(0.3, 8.0, 80.0, 20.0, 1.5, 0.01, rng, mv, sc);
        best_moves = mv; best_score = sc;
    }

    int iter = 0;
    while (true) {
        iter++;
        // Random parameters
        double a = rng.next_double() * 0.8;              // [0, 0.8]
        double b = rng.next_double() * 18.0;             // [0, 18]
        double pen0 = 40.0 + rng.next_double() * 120.0;  // [40,160]
        double pen1 = rng.next_double() * 50.0;          // [0,50]
        double noiseAmp = rng.next_double() * 5.0;       // [0,5]
        double eps = rng.next_double() * 0.05;           // [0,0.05]

        string mv; int sc;
        attempt(a, b, pen0, pen1, noiseAmp, eps, rng, mv, sc);
        if (sc > best_score) {
            best_score = sc;
            best_moves = mv;
        }

        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t_start).count();
        if (elapsed > TIME_LIMIT) break;
    }

    cout << best_moves << '\n';
    return 0;
}