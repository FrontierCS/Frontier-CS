#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') { neg = true; c = read(); }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline bool isEmpty(const vector<uint64_t> &a) {
    for (uint64_t x : a) if (x) return false;
    return true;
}

static inline long long popcountAnd(const vector<uint64_t> &uncovered, const vector<uint64_t> &masks, int s, int blocks) {
    long long g = 0;
    const uint64_t *pm = &masks[(size_t)s * blocks];
    for (int b = 0; b < blocks; b++) g += __builtin_popcountll(pm[b] & uncovered[b]);
    return g;
}

static inline void andNotInplace(vector<uint64_t> &uncovered, const vector<uint64_t> &masks, int s, int blocks) {
    const uint64_t *pm = &masks[(size_t)s * blocks];
    for (int b = 0; b < blocks; b++) uncovered[b] &= ~pm[b];
}

static inline bool coversMask(const vector<uint64_t> &U, const vector<uint64_t> &masks, int t, int blocks) {
    const uint64_t *pm = &masks[(size_t)t * blocks];
    for (int b = 0; b < blocks; b++) {
        if ( (pm[b] & U[b]) != U[b] ) return false;
    }
    return true;
}

static inline int pickAnyUncoveredElement(const vector<uint64_t> &uncovered) {
    for (int b = 0; b < (int)uncovered.size(); b++) {
        uint64_t x = uncovered[b];
        if (!x) continue;
        int bit = __builtin_ctzll(x);
        return b * 64 + bit;
    }
    return -1;
}

static inline void rebuildSelList(vector<int> &selList, const vector<char> &selected) {
    int w = 0;
    for (int x : selList) if (selected[x]) selList[w++] = x;
    selList.resize(w);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<long long> cost(m);
    for (int i = 0; i < m; i++) fs.readInt(cost[i]);

    int blocks = (n + 63) / 64;
    vector<uint64_t> masks((size_t)m * blocks, 0ULL);
    vector<vector<int>> elems(m);
    vector<vector<int>> elemSets(n);

    for (int i = 0; i < n; i++) {
        int k; fs.readInt(k);
        elemSets[i].reserve(k);
        for (int j = 0; j < k; j++) {
            int a; fs.readInt(a);
            --a;
            elemSets[i].push_back(a);
            masks[(size_t)a * blocks + (i >> 6)] |= 1ULL << (i & 63);
            elems[a].push_back(i);
        }
    }

    vector<uint64_t> uncovered(blocks, 0ULL);
    for (int i = 0; i < n; i++) uncovered[i >> 6] |= 1ULL << (i & 63);

    vector<char> selected(m, 0);
    vector<int> selList;
    selList.reserve(min(m, n * 2));

    // Greedy
    while (!isEmpty(uncovered)) {
        int best = -1;
        long long bestGain = 0;

        for (int s = 0; s < m; s++) {
            if (selected[s]) continue;
            long long gain = popcountAnd(uncovered, masks, s, blocks);
            if (gain <= 0) continue;

            if (best == -1) {
                best = s; bestGain = gain;
            } else {
                __int128 lhs = (__int128)gain * (__int128)cost[best];
                __int128 rhs = (__int128)bestGain * (__int128)cost[s];
                if (lhs > rhs) {
                    best = s; bestGain = gain;
                } else if (lhs == rhs) {
                    if (cost[s] < cost[best] || (cost[s] == cost[best] && gain > bestGain)) {
                        best = s; bestGain = gain;
                    }
                }
            }
        }

        if (best == -1) break;
        selected[best] = 1;
        selList.push_back(best);
        andNotInplace(uncovered, masks, best, blocks);
    }

    // Fallback: cover remaining elements individually (if any)
    while (!isEmpty(uncovered)) {
        int e = pickAnyUncoveredElement(uncovered);
        if (e < 0 || e >= n) break;
        long long bestC = (1LL<<62);
        int bestS = -1;
        for (int s : elemSets[e]) {
            if (selected[s]) continue;
            if (cost[s] < bestC) { bestC = cost[s]; bestS = s; }
        }
        if (bestS == -1) break;
        selected[bestS] = 1;
        selList.push_back(bestS);
        andNotInplace(uncovered, masks, bestS, blocks);
    }

    // Build cover counts
    vector<int> covercnt(n, 0);
    for (int s : selList) {
        if (!selected[s]) continue;
        for (int e : elems[s]) covercnt[e]++;
    }

    auto removeSet = [&](int s) {
        selected[s] = 0;
        for (int e : elems[s]) covercnt[e]--;
    };
    auto addSet = [&](int s) {
        selected[s] = 1;
        selList.push_back(s);
        for (int e : elems[s]) covercnt[e]++;
    };

    // Remove redundants
    {
        bool changed = true;
        while (changed) {
            changed = false;
            for (int s : selList) {
                if (!selected[s]) continue;
                bool canRem = true;
                for (int e : elems[s]) {
                    if (covercnt[e] <= 1) { canRem = false; break; }
                }
                if (canRem) {
                    removeSet(s);
                    changed = true;
                }
            }
            if (changed) rebuildSelList(selList, selected);
        }
    }

    // Local improvement: replace one set by cheaper set covering its unique elements
    auto tStart = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 9.5;

    auto timeOk = [&]() -> bool {
        auto now = chrono::steady_clock::now();
        double sec = chrono::duration<double>(now - tStart).count();
        return sec < TIME_LIMIT_SEC;
    };

    bool improved = true;
    while (improved && timeOk()) {
        improved = false;

        for (int idx = 0; idx < (int)selList.size() && timeOk(); idx++) {
            int s = selList[idx];
            if (!selected[s]) continue;

            vector<uint64_t> U(blocks, 0ULL);
            int uniqCnt = 0;
            for (int e : elems[s]) {
                if (covercnt[e] == 1) {
                    U[e >> 6] |= 1ULL << (e & 63);
                    uniqCnt++;
                }
            }

            if (uniqCnt == 0) {
                removeSet(s);
                improved = true;
                continue;
            }

            int bestT = -1;
            long long bestTC = (1LL<<62);
            for (int t = 0; t < m; t++) {
                if (selected[t]) continue;
                if (cost[t] >= cost[s]) continue;
                if (cost[t] >= bestTC) continue;
                if (coversMask(U, masks, t, blocks)) {
                    bestT = t;
                    bestTC = cost[t];
                }
            }

            if (bestT != -1) {
                // Add t then remove s
                addSet(bestT);
                removeSet(s);
                improved = true;
            }
        }

        if (improved) {
            rebuildSelList(selList, selected);
            bool changed = true;
            while (changed) {
                changed = false;
                for (int s : selList) {
                    if (!selected[s]) continue;
                    bool canRem = true;
                    for (int e : elems[s]) {
                        if (covercnt[e] <= 1) { canRem = false; break; }
                    }
                    if (canRem) {
                        removeSet(s);
                        changed = true;
                    }
                }
                if (changed) rebuildSelList(selList, selected);
            }
        }
    }

    // Ensure coverage (paranoid)
    for (int e = 0; e < n; e++) {
        if (covercnt[e] > 0) continue;
        long long bestC = (1LL<<62);
        int bestS = -1;
        for (int s : elemSets[e]) {
            if (cost[s] < bestC) { bestC = cost[s]; bestS = s; }
        }
        if (bestS != -1 && !selected[bestS]) addSet(bestS);
        else if (bestS != -1 && selected[bestS]) {
            // already selected but covercnt says 0 => should not happen
            for (int x : elems[bestS]) covercnt[x]++;
        }
    }
    rebuildSelList(selList, selected);

    // Output
    cout << selList.size() << "\n";
    for (size_t i = 0; i < selList.size(); i++) {
        if (i) cout << ' ';
        cout << (selList[i] + 1);
    }
    cout << "\n";
    return 0;
}