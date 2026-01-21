#include <bits/stdc++.h>
using namespace std;

static int K, N;
static long long queryCount = 0;
static mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

static inline void die() {
    exit(0);
}

static vector<pair<int,int>> ask(int x, int y, int z) {
    if (x == y || y == z || x == z) die();
    cout << "? " << x << " " << y << " " << z << "\n";
    cout.flush();
    ++queryCount;

    int r;
    if (!(cin >> r)) die();
    if (r < 0) die();
    vector<pair<int,int>> res;
    res.reserve(r);
    for (int i = 0; i < r; i++) {
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        res.push_back({a, b});
    }
    return res;
}

static inline bool containsPair(const vector<pair<int,int>>& v, int a, int b) {
    if (a > b) swap(a, b);
    for (auto &p : v) if (p.first == a && p.second == b) return true;
    return false;
}

static bool verifyAdjacent(int a, int b) {
    for (int c = 0; c < N; c++) {
        if (c == a || c == b) continue;
        auto res = ask(a, b, c);
        if (!containsPair(res, a, b)) return false;
    }
    return true;
}

static inline int randint(int l, int r) {
    uniform_int_distribution<int> dist(l, r);
    return dist(rng);
}

static inline int randVertex() {
    return randint(0, N - 1);
}

static int randVertexNot(int a) {
    int x;
    do x = randVertex(); while (x == a);
    return x;
}

static int randVertexNot2(int a, int b) {
    int x;
    do x = randVertex(); while (x == a || x == b);
    return x;
}

static int approximateFarthestFrom(int a, int iters) {
    int b = randVertexNot(a);
    int tries = 0;
    while (tries < iters) {
        int c = randVertexNot2(a, b);
        auto res = ask(a, b, c);
        bool ab = containsPair(res, a, b);
        bool ac = containsPair(res, min(a, c), max(a, c));
        // If ab is minimal and ac is not, then d(a,b) < d(a,c) => c is farther than b => replace b.
        if (ab && !ac) b = c;
        else if (ab && ac) { // tie on distance to a, random step to diversify
            if (randint(0, 1)) b = c;
        }
        // else: either ac is minimal (keep b) or (b,c) is minimal (no info)
        tries++;
    }
    return b;
}

static bool goodPivotPair(int a, int b, int checks, int threshold) {
    int bad = 0;
    for (int i = 0; i < checks; i++) {
        int x = randVertexNot2(a, b);
        auto res = ask(x, a, b);
        bool xa = containsPair(res, min(x, a), max(x, a));
        bool xb = containsPair(res, min(x, b), max(x, b));
        bool ab = containsPair(res, min(a, b), max(a, b));
        if (ab && !xa && !xb) bad++;
    }
    return bad <= threshold;
}

static pair<int,int> findAdjacentPair() {
    vector<int> perm(N);
    iota(perm.begin(), perm.end(), 0);

    for (int attempt = 0; attempt < 8; attempt++) {
        shuffle(perm.begin(), perm.end(), rng);
        int a = perm[0], b = perm[1];

        for (int i = 2; i < N; i++) {
            int c = perm[i];
            auto res = ask(a, b, c);
            pair<int,int> chosen = res[0];
            // Prefer a pair involving c if available.
            for (auto &p : res) {
                if (p.first == c || p.second == c) {
                    chosen = p;
                    break;
                }
            }
            a = chosen.first;
            b = chosen.second;
        }

        if (verifyAdjacent(a, b)) return {a, b};
    }

    // Fallback: try a few random reductions from different seeds
    for (int attempt = 0; attempt < 8; attempt++) {
        int a = randVertex();
        int b = randVertexNot(a);
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int c : order) {
            if (c == a || c == b) continue;
            auto res = ask(a, b, c);
            pair<int,int> chosen = res[0];
            for (auto &p : res) {
                if (p.first == c || p.second == c) {
                    chosen = p;
                    break;
                }
            }
            a = chosen.first;
            b = chosen.second;
        }
        if (verifyAdjacent(a, b)) return {a, b};
    }

    // As a last resort, try all pairs with random witnesses (should not happen on random tests)
    for (int a = 0; a < N; a++) {
        for (int b = a + 1; b < N; b++) {
            if (verifyAdjacent(a, b)) return {a, b};
        }
    }
    die();
    return {-1, -1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> K >> N;
    if (!cin) return 0;

    if (N == 3) {
        cout << "! 0 1 2\n";
        cout.flush();
        return 0;
    }

    auto adj = findAdjacentPair();
    int start0 = adj.first, start1 = adj.second;

    int t = min(10, max(1, N - 1));
    vector<pair<int,int>> piv;
    piv.reserve(t);

    const int FAR_ITERS = 28;
    const int GOOD_CHECKS = 6;
    const int GOOD_THRESHOLD = 2;

    for (int i = 0; i < t; i++) {
        pair<int,int> bestPair = {0, 1};
        bool got = false;
        for (int rep = 0; rep < 12 && !got; rep++) {
            int a = randVertex();
            int b = approximateFarthestFrom(a, FAR_ITERS);
            if (a == b) continue;
            if (goodPivotPair(a, b, GOOD_CHECKS, GOOD_THRESHOLD)) {
                bestPair = {a, b};
                got = true;
            } else {
                bestPair = {a, b};
            }
        }
        piv.push_back(bestPair);
    }

    vector<long long> pow3(t + 1, 1);
    for (int i = 1; i <= t; i++) pow3[i] = pow3[i - 1] * 3LL;

    vector<vector<uint8_t>> digits(N, vector<uint8_t>(t, 2));
    vector<long long> sig(N, 0);

    for (int x = 0; x < N; x++) {
        long long s = 0, mult = 1;
        for (int i = 0; i < t; i++) {
            int a = piv[i].first, b = piv[i].second;
            int d = 2;
            if (x == a) d = 0;
            else if (x == b) d = 1;
            else {
                auto res = ask(x, a, b);
                bool xa = containsPair(res, min(x, a), max(x, a));
                bool xb = containsPair(res, min(x, b), max(x, b));
                if (xa && !xb) d = 0;
                else if (xb && !xa) d = 1;
                else if (xa && xb) d = 0; // tie
                else d = 2; // {a,b} minimal or ambiguous
            }
            digits[x][i] = (uint8_t)d;
            s += mult * d;
            mult *= 3LL;
        }
        sig[x] = s;
    }

    vector<vector<long long>> masked1(N, vector<long long>(t, 0));
    for (int v = 0; v < N; v++) {
        for (int i = 0; i < t; i++) {
            long long m = 0, mult = 1;
            for (int j = 0; j < t; j++) if (j != i) {
                m += mult * digits[v][j];
                mult *= 3LL;
            }
            masked1[v][i] = m;
        }
    }

    vector<pair<int,int>> pairPos;
    vector<vector<long long>> masked2;
    if (t >= 2) {
        for (int i = 0; i < t; i++)
            for (int j = i + 1; j < t; j++)
                pairPos.push_back({i, j});
        int P = (int)pairPos.size();
        masked2.assign(N, vector<long long>(P, 0));
        for (int v = 0; v < N; v++) {
            for (int idx = 0; idx < P; idx++) {
                int i = pairPos[idx].first;
                int j = pairPos[idx].second;
                long long m = 0, mult = 1;
                for (int k = 0; k < t; k++) if (k != i && k != j) {
                    m += mult * digits[v][k];
                    mult *= 3LL;
                }
                masked2[v][idx] = m;
            }
        }
    }

    unordered_map<long long, vector<int>> bucket0;
    unordered_map<long long, vector<int>> bucket1;
    unordered_map<long long, vector<int>> bucket2;
    bucket0.reserve(N * 2);
    bucket1.reserve(N * t * 2);
    bucket2.reserve(N * 2);

    for (int v = 0; v < N; v++) {
        bucket0[sig[v]].push_back(v);
    }

    long long base1 = (t >= 1) ? pow3[t - 1] : 1;
    for (int v = 0; v < N; v++) {
        for (int i = 0; i < t; i++) {
            long long key = (long long)i * base1 + masked1[v][i];
            bucket1[key].push_back(v);
        }
    }

    long long base2 = 1;
    if (t >= 2) base2 = pow3[t - 2];
    if (t >= 2) {
        int P = (int)pairPos.size();
        bucket2.reserve(N * P / 2 + 1);
        for (int v = 0; v < N; v++) {
            for (int idx = 0; idx < P; idx++) {
                long long key = (long long)idx * base2 + masked2[v][idx];
                bucket2[key].push_back(v);
            }
        }
    }

    auto isNeighbor = [&](int cur, int prev, int cand) -> bool {
        auto res = ask(cur, prev, cand);
        return containsPair(res, min(cur, cand), max(cur, cand));
    };

    vector<char> used(N, 0);
    vector<int> ans;
    ans.reserve(N);
    ans.push_back(start0);
    ans.push_back(start1);
    used[start0] = used[start1] = 1;

    vector<int> seen(N, 0);
    int stamp = 1;

    auto gatherAndTry = [&](int prev, int cur, bool use2wild) -> int {
        vector<int> candList;
        candList.reserve(64);

        auto addVec = [&](const vector<int> *pv) {
            if (!pv) return;
            for (int x : *pv) {
                if (seen[x] == stamp) continue;
                seen[x] = stamp;
                candList.push_back(x);
            }
        };

        auto it0 = bucket0.find(sig[cur]);
        if (it0 != bucket0.end()) addVec(&it0->second);

        for (int i = 0; i < t; i++) {
            long long key = (long long)i * base1 + masked1[cur][i];
            auto it1 = bucket1.find(key);
            if (it1 != bucket1.end()) addVec(&it1->second);
        }

        if (use2wild && t >= 2) {
            int P = (int)pairPos.size();
            for (int idx = 0; idx < P; idx++) {
                long long key = (long long)idx * base2 + masked2[cur][idx];
                auto it2 = bucket2.find(key);
                if (it2 != bucket2.end()) addVec(&it2->second);
            }
        }

        for (int c : candList) {
            if (c == prev || c == cur) continue;
            if (used[c]) continue;
            if (isNeighbor(cur, prev, c)) return c;
        }
        return -1;
    };

    auto similarityFallback = [&](int prev, int cur) -> int {
        vector<pair<int,int>> scored;
        scored.reserve(N);
        for (int c = 0; c < N; c++) {
            if (c == prev || c == cur) continue;
            if (used[c]) continue;
            int sc = 0;
            for (int i = 0; i < t; i++) sc += (digits[c][i] == digits[cur][i]);
            scored.push_back({-sc, c});
        }
        sort(scored.begin(), scored.end());
        for (auto &p : scored) {
            int c = p.second;
            if (isNeighbor(cur, prev, c)) return c;
        }
        for (int c = 0; c < N; c++) {
            if (c == prev || c == cur) continue;
            if (used[c]) continue;
            if (isNeighbor(cur, prev, c)) return c;
        }
        return -1;
    };

    while ((int)ans.size() < N) {
        int prev = ans[(int)ans.size() - 2];
        int cur  = ans[(int)ans.size() - 1];

        int nxt = -1;
        stamp++;
        if (stamp == INT_MAX) { fill(seen.begin(), seen.end(), 0); stamp = 1; }

        nxt = gatherAndTry(prev, cur, false);
        if (nxt == -1) {
            stamp++;
            if (stamp == INT_MAX) { fill(seen.begin(), seen.end(), 0); stamp = 1; }
            nxt = gatherAndTry(prev, cur, true);
        }
        if (nxt == -1) {
            nxt = similarityFallback(prev, cur);
        }
        if (nxt < 0) die();
        used[nxt] = 1;
        ans.push_back(nxt);
    }

    cout << "!";
    for (int x : ans) cout << " " << x;
    cout << "\n";
    cout.flush();
    return 0;
}