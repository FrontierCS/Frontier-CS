#include <bits/stdc++.h>
using namespace std;

struct XorShift {
    uint64_t x;
    XorShift(uint64_t seed = 88172645463393265ull) { x = seed; }
    inline uint64_t next() { x ^= x<<7; return x ^= x>>9; }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline double next_double() { return (next() & ((1ull<<53)-1)) * (1.0 / (double)(1ull<<53)); }
    inline int randint(int l, int r) { // [l, r]
        return l + (int)(next_u32() % (uint32_t)(r - l + 1));
    }
};

static const int H = 50;
static const int W = 50;
static const int N = H * W;

struct Neighbor {
    int to;
    char dir;
};

struct RunResult {
    string path;
    long long score;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    vector<int> t(N), p(N);
    cin >> si >> sj;
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) {
        int x; cin >> x;
        t[i*W+j] = x;
    }
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) {
        int x; cin >> x;
        p[i*W+j] = x;
    }

    int M = 0;
    for (int i = 0; i < N; i++) M = max(M, t[i] + 1);

    // Precompute neighbors excluding moves within the same tile
    vector<array<int,4>> nb_id(N);
    vector<array<char,4>> nb_dir(N);
    vector<int> nb_cnt(N, 0);
    auto inb = [&](int i, int j){ return (0 <= i && i < H && 0 <= j && j < W); };

    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) {
        int id = i*W + j;
        int cnt = 0;
        const int ti = t[id];
        // U
        if (inb(i-1,j)) {
            int id2 = (i-1)*W + j;
            if (t[id2] != ti) { nb_id[id][cnt] = id2; nb_dir[id][cnt] = 'U'; cnt++; }
        }
        // D
        if (inb(i+1,j)) {
            int id2 = (i+1)*W + j;
            if (t[id2] != ti) { nb_id[id][cnt] = id2; nb_dir[id][cnt] = 'D'; cnt++; }
        }
        // L
        if (inb(i,j-1)) {
            int id2 = i*W + (j-1);
            if (t[id2] != ti) { nb_id[id][cnt] = id2; nb_dir[id][cnt] = 'L'; cnt++; }
        }
        // R
        if (inb(i,j+1)) {
            int id2 = i*W + (j+1);
            if (t[id2] != ti) { nb_id[id][cnt] = id2; nb_dir[id][cnt] = 'R'; cnt++; }
        }
        nb_cnt[id] = cnt;
    }

    auto compute_deg = [&](int id, const vector<char>& visited, int extra_tile1 = -1) {
        int d = 0;
        int cnt = nb_cnt[id];
        for (int k = 0; k < cnt; k++) {
            int to = nb_id[id][k];
            int tt = t[to];
            if (visited[tt]) continue;
            if (tt == extra_tile1) continue;
            d++;
        }
        return d;
    };

    struct Params {
        double w_p1;
        double w_p2;
        double w_deg1;
        double w_deg2;
        double discount;
        double deadPenalty;
        double tieNoise;
    };

    auto evaluate_move = [&](int cur, int nxt, const vector<char>& visited, const Params& param) {
        // immediate contributions
        double s = param.w_p1 * p[nxt];

        int deg1 = compute_deg(nxt, visited);
        s += param.w_deg1 * deg1;

        // lookahead 1 step with excluding tile of nxt
        double best2 = 0.0;
        int cnt2 = nb_cnt[nxt];
        int tileN = t[nxt];
        for (int k = 0; k < cnt2; k++) {
            int nn = nb_id[nxt][k];
            int tnn = t[nn];
            if (visited[tnn]) continue;
            // after moving to nxt, tileN becomes visited; so from nn we must exclude tileN
            if (tnn == tileN) continue; // not necessary, but safe
            int deg2 = compute_deg(nn, visited, tileN);
            double s2 = param.w_p2 * p[nn] + param.w_deg2 * deg2;
            if (s2 > best2) best2 = s2;
        }
        s += param.discount * best2;
        return s;
    };

    int start_id = si * W + sj;

    auto simulate = [&](const Params& param, XorShift& rng, double endTime, chrono::steady_clock::time_point t0) -> RunResult {
        vector<char> visited(M, 0);
        int cur = start_id;
        visited[t[cur]] = 1;
        long long score = p[cur];
        string path;
        path.reserve(N);

        while (true) {
            // Check time
            if (chrono::duration<double>(chrono::steady_clock::now() - t0).count() > endTime) break;

            // Gather candidates
            int cnt = nb_cnt[cur];
            vector<int> cands;
            cands.reserve(4);
            for (int k = 0; k < cnt; k++) {
                int to = nb_id[cur][k];
                if (!visited[t[to]]) cands.push_back(k);
            }
            if (cands.empty()) break;

            // Check if any non-deadend candidates exist
            bool hasNonDead = false;
            for (int idx : cands) {
                int to = nb_id[cur][idx];
                int d = compute_deg(to, visited);
                if (d > 0) { hasNonDead = true; break; }
            }

            // Evaluate and choose best
            double bestEval = -1e100;
            int bestIdx = -1;
            for (int idx : cands) {
                int to = nb_id[cur][idx];

                double e = evaluate_move(cur, to, visited, param);
                // Penalize deadend if alternatives exist
                if (hasNonDead) {
                    int d1 = compute_deg(to, visited);
                    if (d1 == 0) e -= param.deadPenalty;
                }
                // small random noise to diversify
                e += (rng.next_double() - 0.5) * param.tieNoise;

                if (e > bestEval) {
                    bestEval = e;
                    bestIdx = idx;
                }
            }
            if (bestIdx == -1) break;

            // Move
            int to = nb_id[cur][bestIdx];
            visited[t[to]] = 1;
            score += p[to];
            path.push_back(nb_dir[cur][bestIdx]);
            cur = to;
        }

        return {path, score};
    };

    auto t0 = chrono::steady_clock::now();
    double timeLimit = 1.95; // seconds
    XorShift rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // First quick deterministic run with decent parameters
    Params baseParam;
    baseParam.w_p1 = 1.0;
    baseParam.w_p2 = 0.9;
    baseParam.w_deg1 = 22.0;
    baseParam.w_deg2 = 16.0;
    baseParam.discount = 0.65;
    baseParam.deadPenalty = 120.0;
    baseParam.tieNoise = 0.01;

    RunResult best = simulate(baseParam, rng, timeLimit, t0);
    long long bestScore = best.score;
    string bestPath = best.path;

    // Randomized runs with varying parameters
    // Keep running until time runs out, keep best
    while (chrono::duration<double>(chrono::steady_clock::now() - t0).count() < timeLimit) {
        Params par;
        par.w_p1 = 1.0 + 0.2 * (rng.next_double() - 0.5);   // ~[0.9,1.1]
        par.w_p2 = 0.8 + 0.4 * rng.next_double();           // [0.8,1.2]
        par.w_deg1 = 12.0 + rng.next_u32() % 28;            // [12,39]
        par.w_deg2 = 8.0 + rng.next_u32() % 22;             // [8,29]
        par.discount = 0.55 + 0.35 * rng.next_double();     // [0.55,0.9]
        par.deadPenalty = 80.0 + (rng.next_u32() % 181);    // [80,260]
        par.tieNoise = 0.02;

        RunResult rr = simulate(par, rng, timeLimit, t0);
        if (rr.score > bestScore) {
            bestScore = rr.score;
            bestPath = rr.path;
        }
    }

    cout << bestPath << '\n';
    return 0;
}