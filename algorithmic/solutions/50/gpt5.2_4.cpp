#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
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
        if (c == '-') {
            neg = true;
            c = read();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline int popcount64(uint64_t x) { return __builtin_popcountll(x); }
static inline int ctz64(uint64_t x) { return __builtin_ctzll(x); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    const int MAXB = 7;
    int B = (n + 63) / 64;

    struct SetMask {
        array<uint64_t, MAXB> b{};
    };

    vector<long long> cost(m);
    for (int i = 0; i < m; i++) fs.readInt(cost[i]);

    vector<SetMask> sets(m);
    vector<vector<int>> elemSets(n);

    for (int i = 0; i < n; i++) {
        int k;
        fs.readInt(k);
        elemSets[i].reserve(k);
        for (int j = 0; j < k; j++) {
            int a;
            fs.readInt(a);
            --a;
            if (a < 0 || a >= m) continue;
            elemSets[i].push_back(a);
            int blk = i >> 6;
            int bit = i & 63;
            sets[a].b[blk] |= (1ULL << bit);
        }
        sort(elemSets[i].begin(), elemSets[i].end());
        elemSets[i].erase(unique(elemSets[i].begin(), elemSets[i].end()), elemSets[i].end());
    }

    // uncovered mask
    array<uint64_t, MAXB> uncovered{};
    for (int i = 0; i < MAXB; i++) uncovered[i] = 0;
    for (int i = 0; i < B; i++) uncovered[i] = ~0ULL;
    if (B > 0 && (n & 63)) uncovered[B - 1] = (1ULL << (n & 63)) - 1ULL;
    for (int i = B; i < MAXB; i++) uncovered[i] = 0;

    auto anyUncovered = [&]() -> bool {
        for (int i = 0; i < B; i++) if (uncovered[i]) return true;
        return false;
    };

    auto applySet = [&](int sid) {
        for (int i = 0; i < B; i++) uncovered[i] &= ~sets[sid].b[i];
    };

    vector<char> chosen(m, 0);
    vector<int> selected;

    // Mandatory: elements with exactly one containing set
    for (int i = 0; i < n; i++) {
        if (elemSets[i].empty()) {
            // Impossible to cover; output empty solution (best effort)
            cout << 0 << "\n\n";
            return 0;
        }
        if (elemSets[i].size() == 1) {
            int sid = elemSets[i][0];
            if (!chosen[sid]) {
                chosen[sid] = 1;
                selected.push_back(sid);
                applySet(sid);
            }
        }
    }

    // Greedy selection
    while (anyUncovered()) {
        int bestIdx = -1;
        long long bestCost = 1;
        int bestCnt = 0;

        for (int s = 0; s < m; s++) {
            if (chosen[s]) continue;
            int cnt = 0;
            for (int i = 0; i < B; i++) cnt += popcount64(sets[s].b[i] & uncovered[i]);
            if (cnt <= 0) continue;

            __int128 lhs = (__int128)cnt * (__int128)bestCost;
            __int128 rhs = (__int128)bestCnt * (__int128)cost[s];
            if (bestIdx == -1 || lhs > rhs ||
                (lhs == rhs && (cost[s] < bestCost || (cost[s] == bestCost && cnt > bestCnt)))) {
                bestIdx = s;
                bestCnt = cnt;
                bestCost = cost[s];
            }
        }

        if (bestIdx == -1) break; // fallback handles remaining
        chosen[bestIdx] = 1;
        selected.push_back(bestIdx);
        applySet(bestIdx);
    }

    // Fallback: cover remaining uncovered elements with cheapest set per element
    while (anyUncovered()) {
        int e = -1;
        for (int blk = 0; blk < B && e == -1; blk++) {
            if (uncovered[blk]) {
                int bit = ctz64(uncovered[blk]);
                e = (blk << 6) + bit;
                if (e >= n) e = -1;
            }
        }
        if (e == -1) break;
        long long bestC = (1LL << 62);
        int bestS = -1;
        for (int s : elemSets[e]) {
            if (cost[s] < bestC) {
                bestC = cost[s];
                bestS = s;
            }
        }
        if (bestS == -1) break; // should not happen if feasible
        if (!chosen[bestS]) {
            chosen[bestS] = 1;
            selected.push_back(bestS);
        }
        applySet(bestS);
    }

    // Compute coverage counts per element for pruning
    vector<int> cov(n, 0);
    auto addCov = [&](int sid, int delta) {
        for (int blk = 0; blk < B; blk++) {
            uint64_t x = sets[sid].b[blk];
            while (x) {
                int t = ctz64(x);
                int e = (blk << 6) + t;
                if (e < n) cov[e] += delta;
                x &= x - 1;
            }
        }
    };
    for (int sid : selected) addCov(sid, +1);

    // Try to remove redundant sets, prioritize higher cost removal
    vector<int> order = selected;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (cost[a] != cost[b]) return cost[a] > cost[b];
        return a < b;
    });

    vector<char> keep(m, 0);
    for (int sid : selected) keep[sid] = 1;

    for (int sid : order) {
        bool canRemove = true;
        for (int blk = 0; blk < B && canRemove; blk++) {
            uint64_t x = sets[sid].b[blk];
            while (x) {
                int t = ctz64(x);
                int e = (blk << 6) + t;
                if (e < n && cov[e] <= 1) {
                    canRemove = false;
                    break;
                }
                x &= x - 1;
            }
        }
        if (canRemove) {
            keep[sid] = 0;
            addCov(sid, -1);
        }
    }

    vector<int> finalSel;
    finalSel.reserve(selected.size());
    for (int sid : selected) if (keep[sid]) finalSel.push_back(sid);

    // Final validity check; if missing any element, add cheapest cover for missing elements
    {
        array<uint64_t, MAXB> covered{};
        for (int i = 0; i < MAXB; i++) covered[i] = 0;
        for (int sid : finalSel) {
            for (int blk = 0; blk < B; blk++) covered[blk] |= sets[sid].b[blk];
        }
        array<uint64_t, MAXB> need{};
        for (int i = 0; i < MAXB; i++) need[i] = 0;
        for (int blk = 0; blk < B; blk++) need[blk] = uncovered[blk] = 0; // reuse
        // rebuild need = all elements - covered
        for (int blk = 0; blk < B; blk++) need[blk] = ~covered[blk];
        if (B > 0 && (n & 63)) need[B - 1] &= (1ULL << (n & 63)) - 1ULL;
        for (int blk = B; blk < MAXB; blk++) need[blk] = 0;

        auto anyNeed = [&]() -> bool {
            for (int blk = 0; blk < B; blk++) if (need[blk]) return true;
            return false;
        };

        vector<char> inFinal(m, 0);
        for (int sid : finalSel) inFinal[sid] = 1;

        while (anyNeed()) {
            int e = -1;
            for (int blk = 0; blk < B && e == -1; blk++) {
                if (need[blk]) {
                    int bit = ctz64(need[blk]);
                    e = (blk << 6) + bit;
                    if (e >= n) e = -1;
                }
            }
            if (e == -1) break;

            int bestS = -1;
            long long bestC = (1LL << 62);
            for (int s : elemSets[e]) {
                if (cost[s] < bestC) {
                    bestC = cost[s];
                    bestS = s;
                }
            }
            if (bestS == -1) break;
            if (!inFinal[bestS]) {
                inFinal[bestS] = 1;
                finalSel.push_back(bestS);
                for (int blk = 0; blk < B; blk++) covered[blk] |= sets[bestS].b[blk];
            }
            for (int blk = 0; blk < B; blk++) need[blk] &= ~sets[bestS].b[blk];
        }
    }

    // Output
    cout << finalSel.size() << "\n";
    for (size_t i = 0; i < finalSel.size(); i++) {
        if (i) cout << ' ';
        cout << (finalSel[i] + 1);
    }
    cout << "\n";
    return 0;
}