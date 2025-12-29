#include <bits/stdc++.h>
using namespace std;

static inline uint32_t xorshift32(uint32_t &x) {
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;

    vector<string> h(20);
    for (int i = 0; i < 20; i++) cin >> h[i];
    vector<string> v(19);
    for (int i = 0; i < 19; i++) cin >> v[i];

    auto canMove = [&](int i, int j, int dir) -> bool {
        // 0:U 1:D 2:L 3:R
        if (dir == 0) {
            if (i == 0) return false;
            return v[i - 1][j] == '0';
        } else if (dir == 1) {
            if (i == 19) return false;
            return v[i][j] == '0';
        } else if (dir == 2) {
            if (j == 0) return false;
            return h[i][j - 1] == '0';
        } else {
            if (j == 19) return false;
            return h[i][j] == '0';
        }
    };

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};
    auto dirFromChar = [&](char c) -> int {
        if (c == 'U') return 0;
        if (c == 'D') return 1;
        if (c == 'L') return 2;
        return 3;
    };

    auto bfsShortest = [&]() -> string {
        const int N = 400;
        vector<int> prev(N, -1);
        vector<char> prevMove(N, 0);
        queue<int> q;
        int s = si * 20 + sj;
        int t = ti * 20 + tj;
        prev[s] = s;
        q.push(s);

        while (!q.empty()) {
            int cur = q.front(); q.pop();
            if (cur == t) break;
            int i = cur / 20, j = cur % 20;
            for (int d = 0; d < 4; d++) {
                if (!canMove(i, j, d)) continue;
                int ni = i + di[d], nj = j + dj[d];
                int nxt = ni * 20 + nj;
                if (prev[nxt] != -1) continue;
                prev[nxt] = cur;
                prevMove[nxt] = dc[d];
                q.push(nxt);
            }
        }

        if (prev[t] == -1) return "";
        string path;
        for (int cur = t; cur != s; cur = prev[cur]) path.push_back(prevMove[cur]);
        reverse(path.begin(), path.end());
        return path;
    };

    auto dijkstraTurn = [&](int turnW) -> string {
        const int W = 20, H = 20;
        const int STATES = W * H * 5;
        const int INF = 1e9;

        auto enc = [&](int i, int j, int last) {
            return ((i * 20 + j) * 5 + last);
        };
        auto dec = [&](int id, int &i, int &j, int &last) {
            last = id % 5;
            int cell = id / 5;
            i = cell / 20;
            j = cell % 20;
        };

        vector<int> dist(STATES, INF);
        vector<int> parent(STATES, -1);
        vector<char> pmove(STATES, 0);

        int sid = enc(si, sj, 4);
        dist[sid] = 0;

        struct PQN {
            int d, id;
            bool operator<(const PQN &o) const { return d > o.d; }
        };
        priority_queue<PQN> pq;
        pq.push({0, sid});

        while (!pq.empty()) {
            auto [d, id] = pq.top(); pq.pop();
            if (d != dist[id]) continue;
            int i, j, last;
            dec(id, i, j, last);
            for (int nd = 0; nd < 4; nd++) {
                if (!canMove(i, j, nd)) continue;
                int ni = i + di[nd], nj = j + dj[nd];
                int nid = enc(ni, nj, nd);
                int add = 1 + ((last != 4 && last != nd) ? turnW : 0);
                if (dist[nid] > d + add) {
                    dist[nid] = d + add;
                    parent[nid] = id;
                    pmove[nid] = dc[nd];
                    pq.push({dist[nid], nid});
                }
            }
        }

        int bestId = -1;
        int bestD = INF;
        for (int last = 0; last < 4; last++) {
            int tid = enc(ti, tj, last);
            if (dist[tid] < bestD) {
                bestD = dist[tid];
                bestId = tid;
            }
        }
        if (bestId == -1) return "";

        string path;
        for (int cur = bestId; cur != sid; cur = parent[cur]) {
            if (cur < 0) return "";
            path.push_back(pmove[cur]);
        }
        reverse(path.begin(), path.end());
        return path;
    };

    auto reversePath = [&](const string &s) -> string {
        string r;
        r.reserve(s.size());
        for (int k = (int)s.size() - 1; k >= 0; k--) {
            char c = s[k];
            if (c == 'U') r.push_back('D');
            else if (c == 'D') r.push_back('U');
            else if (c == 'L') r.push_back('R');
            else r.push_back('L');
        }
        return r;
    };

    vector<string> basePaths;
    string P = bfsShortest();
    if (!P.empty()) basePaths.push_back(P);

    int wmax = (int)llround(30.0 * p);
    vector<int> ws = {0, max(1, wmax / 2), wmax, min(20, wmax + 3), min(25, wmax + 7), 15};
    sort(ws.begin(), ws.end());
    ws.erase(unique(ws.begin(), ws.end()), ws.end());
    for (int w : ws) {
        if (w == 0) continue;
        string Q = dijkstraTurn(w);
        if (!Q.empty()) basePaths.push_back(Q);
    }

    auto clamp200 = [&](string s) -> string {
        if (s.size() > 200) s.resize(200);
        return s;
    };

    vector<string> candidates;
    auto addCand = [&](const string &s) {
        candidates.push_back(clamp200(s));
    };

    for (const string &B : basePaths) {
        addCand(B);
        // repeat
        for (int k = 2; k <= 5; k++) {
            string rep;
            rep.reserve(min<size_t>(200, B.size() * k));
            for (int i = 0; i < k && rep.size() + B.size() <= 200; i++) rep += B;
            if (!rep.empty()) addCand(rep);
        }
        // forward + backward + forward
        string rev = reversePath(B);
        if (B.size() + rev.size() + B.size() <= 200) addCand(B + rev + B);
        // forward + backward
        if (B.size() + rev.size() <= 200) addCand(B + rev);
    }

    // As a fallback, at least output something
    if (candidates.empty()) {
        cout << "\n";
        return 0;
    }

    // Remove duplicates
    {
        unordered_set<string> seen;
        vector<string> uniq;
        uniq.reserve(candidates.size());
        for (auto &s : candidates) {
            if (seen.insert(s).second) uniq.push_back(s);
        }
        candidates.swap(uniq);
    }

    // Precompute random values for simulation
    const int TRIALS = 4000;
    const int LMAX = 200;
    vector<array<uint32_t, LMAX>> rnd(TRIALS);
    uint32_t seed = 123456789u;
    for (int t = 0; t < TRIALS; t++) {
        for (int k = 0; k < LMAX; k++) rnd[t][k] = xorshift32(seed);
    }

    uint64_t thr64 = (uint64_t)(p * (double)(1ULL << 32));
    uint32_t thr = (uint32_t)thr64;

    auto simulate = [&](const string &route) -> double {
        int L = (int)route.size();
        if (L == 0) return 0.0;
        long long sum = 0;
        for (int tr = 0; tr < TRIALS; tr++) {
            int i = si, j = sj;
            int score = 0;
            for (int step = 1; step <= L; step++) {
                // forgetting?
                if (rnd[tr][step - 1] >= thr) {
                    int d = dirFromChar(route[step - 1]);
                    if (canMove(i, j, d)) {
                        i += di[d];
                        j += dj[d];
                    }
                }
                if (i == ti && j == tj) {
                    score = 401 - step;
                    break;
                }
            }
            sum += score;
        }
        return (double)sum / (double)TRIALS;
    };

    string best = candidates[0];
    double bestVal = -1.0;
    for (const auto &cand : candidates) {
        double val = simulate(cand);
        if (val > bestVal) {
            bestVal = val;
            best = cand;
        }
    }

    if (best.size() > 200) best.resize(200);
    for (char c : best) {
        if (c != 'U' && c != 'D' && c != 'L' && c != 'R') {
            best.clear();
            break;
        }
    }
    cout << best << "\n";
    return 0;
}