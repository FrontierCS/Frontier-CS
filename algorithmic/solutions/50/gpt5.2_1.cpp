#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
#ifdef _WIN32
        return getchar();
#else
        return getchar_unlocked();
#endif
    }
    template <class T>
    bool readInt(T &out) {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = gc();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = gc();
        }
        out = neg ? -val : val;
        return true;
    }
};

static vector<long long> gCost;

struct Node {
    int id;
    int gain;
};

struct Cmp {
    bool operator()(const Node& a, const Node& b) const {
        __int128 lhs = (__int128)gCost[a.id] * (__int128)b.gain;
        __int128 rhs = (__int128)gCost[b.id] * (__int128)a.gain;
        if (lhs != rhs) return lhs > rhs; // higher ratio => lower priority
        if (a.gain != b.gain) return a.gain < b.gain; // prefer larger gain
        if (gCost[a.id] != gCost[b.id]) return gCost[a.id] > gCost[b.id]; // prefer cheaper
        return a.id > b.id;
    }
};

static inline int popcount_mask_and(const vector<uint64_t>& a, const vector<uint64_t>& b) {
    int res = 0;
    for (size_t i = 0; i < a.size(); i++) res += __builtin_popcountll(a[i] & b[i]);
    return res;
}

static inline int gain_of_set(const vector<uint64_t>& setMask, const vector<uint64_t>& uncovered) {
    int res = 0;
    for (size_t i = 0; i < setMask.size(); i++) res += __builtin_popcountll(setMask[i] & uncovered[i]);
    return res;
}

static inline int find_first_uncovered(const vector<uint64_t>& uncovered, int n) {
    for (size_t w = 0; w < uncovered.size(); w++) {
        uint64_t x = uncovered[w];
        if (x) {
            int b = __builtin_ctzll(x);
            int idx = int(w * 64 + b);
            if (idx < n) return idx;
        }
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    gCost.assign(m, 0);
    for (int i = 0; i < m; i++) fs.readInt(gCost[i]);

    const int W = (n + 63) / 64;
    vector<vector<uint64_t>> setMask(m, vector<uint64_t>(W, 0));
    vector<vector<int>> setElems(m);
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
            setElems[a].push_back(i);
            setMask[a][i >> 6] |= (1ULL << (i & 63));
        }
    }

    vector<uint64_t> uncovered(W, ~0ULL);
    if (n % 64 != 0) uncovered.back() = (1ULL << (n % 64)) - 1ULL;

    int remaining = n;

    priority_queue<Node, vector<Node>, Cmp> pq;
    pq = priority_queue<Node, vector<Node>, Cmp>();

    for (int s = 0; s < m; s++) {
        int g = gain_of_set(setMask[s], uncovered);
        if (g > 0) pq.push({s, g});
    }

    vector<char> selected(m, 0);
    vector<int> chosen;
    chosen.reserve(n);

    auto apply_select = [&](int s) {
        if (selected[s]) return;
        int gained = 0;
        for (int w = 0; w < W; w++) {
            uint64_t newly = setMask[s][w] & uncovered[w];
            if (newly) {
                gained += __builtin_popcountll(newly);
                uncovered[w] &= ~setMask[s][w];
            }
        }
        if (gained > 0) {
            remaining -= gained;
        }
        selected[s] = 1;
        chosen.push_back(s);
    };

    while (remaining > 0) {
        if (pq.empty()) break;

        Node cur = pq.top();
        pq.pop();

        int g = gain_of_set(setMask[cur.id], uncovered);
        if (g <= 0) continue;
        if (g != cur.gain) {
            pq.push({cur.id, g});
            continue;
        }

        apply_select(cur.id);
    }

    // Fallback: cover remaining elements by picking cheapest set per uncovered element
    while (remaining > 0) {
        int e = find_first_uncovered(uncovered, n);
        if (e < 0) break;
        long long bestC = LLONG_MAX;
        int bestS = -1;
        for (int s : elemSets[e]) {
            if (gCost[s] < bestC) {
                bestC = gCost[s];
                bestS = s;
            }
        }
        if (bestS < 0) break; // impossible to cover
        apply_select(bestS);
    }

    // Remove redundant selected sets (prefer removing expensive first)
    vector<int> order = chosen;
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (gCost[a] != gCost[b]) return gCost[a] > gCost[b];
        return a > b;
    });

    vector<int> coverCount(n, 0);
    for (int s : chosen) {
        if (!selected[s]) continue;
        for (int e : setElems[s]) coverCount[e]++;
    }

    for (int s : order) {
        if (!selected[s]) continue;
        bool removable = true;
        for (int e : setElems[s]) {
            if (coverCount[e] <= 1) { removable = false; break; }
        }
        if (!removable) continue;
        selected[s] = 0;
        for (int e : setElems[s]) coverCount[e]--;
    }

    vector<int> finalSets;
    finalSets.reserve(m);
    for (int s = 0; s < m; s++) if (selected[s]) finalSets.push_back(s);

    cout << finalSets.size() << "\n";
    for (size_t i = 0; i < finalSets.size(); i++) {
        if (i) cout << ' ';
        cout << (finalSets[i] + 1);
    }
    cout << "\n";
    return 0;
}