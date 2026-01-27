#include <bits/stdc++.h>
using namespace std;

struct InteractiveSolver {
    int k = 0, n = 0;
    int used = 0;

    mt19937 rng{(uint32_t)chrono::steady_clock::now().time_since_epoch().count()};

    static inline uint64_t pairKey(int a, int b) {
        if (a > b) swap(a, b);
        return (uint64_t)a << 32 | (uint32_t)b;
    }

    int ask(int x, int y, int z) {
        if (used >= k) return 0;
        ++used;
        cout << "? " << x << " " << y << " " << z << "\n";
        cout.flush();

        int r;
        if (!(cin >> r)) exit(0);
        int mask = 0;
        for (int i = 0; i < r; i++) {
            int a, b;
            cin >> a >> b;
            if (a > b) swap(a, b);
            int xy_a = min(x, y), xy_b = max(x, y);
            int yz_a = min(y, z), yz_b = max(y, z);
            int xz_a = min(x, z), xz_b = max(x, z);
            if (a == xy_a && b == xy_b) mask |= 1;
            if (a == yz_a && b == yz_b) mask |= 2;
            if (a == xz_a && b == xz_b) mask |= 4;
        }
        return mask;
    }

    bool inMaskPair(int mask, int u, int v, int x, int y, int z) {
        int a = min(u, v), b = max(u, v);
        int xy_a = min(x, y), xy_b = max(x, y);
        int yz_a = min(y, z), yz_b = max(y, z);
        int xz_a = min(x, z), xz_b = max(x, z);
        if (a == xy_a && b == xy_b) return mask & 1;
        if (a == yz_a && b == yz_b) return mask & 2;
        if (a == xz_a && b == xz_b) return mask & 4;
        return false;
    }

    // Returns:
    //  0 -> u is (weakly) closer to x than v (or tie/unknown)
    //  1 -> v is (weakly) closer to x than u
    int closerHeuristic(int x, int u, int v) {
        int mask = ask(x, u, v);
        bool xu = inMaskPair(mask, x, u, x, u, v);
        bool xv = inMaskPair(mask, x, v, x, u, v);
        if (xu && !xv) return 0;
        if (!xu && xv) return 1;
        // inconclusive or tie
        return (u > v); // deterministic tie-break
    }

    int pickCandidate(const vector<int>& ord, int x, int samples) {
        int m = (int)ord.size();
        uniform_int_distribution<int> dist(0, m - 1);
        int cand = ord[dist(rng)];
        for (int i = 1; i < samples; i++) {
            int other = ord[dist(rng)];
            if (cand == other) continue;
            int win = closerHeuristic(x, cand, other);
            if (win == 1) cand = other;
        }
        return cand;
    }

    int findIndex(const vector<int>& ord, int v) {
        for (int i = 0; i < (int)ord.size(); i++) if (ord[i] == v) return i;
        return -1;
    }

    // Choose insertion position near idx by scoring edges in a window.
    int bestEdgeInWindow(const vector<int>& ord, int x, int idx, int W) {
        int m = (int)ord.size();
        int bestPos = 0;
        int bestScore = -1;

        for (int d = -W; d <= W; d++) {
            int j = (idx + d) % m;
            if (j < 0) j += m;
            int a = ord[j];
            int b = ord[(j + 1) % m];

            int mask = ask(a, b, x);
            bool ab = inMaskPair(mask, a, b, a, b, x);
            bool ax = inMaskPair(mask, min(a, x), max(a, x), a, b, x);
            bool bx = inMaskPair(mask, min(b, x), max(b, x), a, b, x);

            int score = 0;
            if (!ab) score += 3;
            if (ax) score += 1;
            if (bx) score += 1;

            // slight bias for closer to endpoints
            if (ax && bx) score += 1;

            if (score > bestScore) {
                bestScore = score;
                bestPos = j + 1; // insert after j
            }
        }
        if (bestPos >= m) bestPos -= m;
        return bestPos;
    }

    bool localCheckAndFix(vector<int>& ord, int posInserted) {
        int m = (int)ord.size();
        int x = ord[posInserted];

        int prev = ord[(posInserted - 1 + m) % m];
        int next = ord[(posInserted + 1) % m];

        int mask = ask(prev, x, next);
        bool prevnext = inMaskPair(mask, min(prev, next), max(prev, next), prev, x, next);
        // If prev-next is minimal, x likely misplaced; attempt swap with next or prev.
        if (prevnext) {
            // Try swap with next
            int pos2 = (posInserted + 1) % m;
            swap(ord[posInserted], ord[pos2]);
            int x2 = ord[pos2];
            int prev2 = ord[(pos2 - 1 + m) % m];
            int next2 = ord[(pos2 + 1) % m];
            int mask2 = ask(prev2, x2, next2);
            bool prev2next2 = inMaskPair(mask2, min(prev2, next2), max(prev2, next2), prev2, x2, next2);
            if (!prev2next2) return true;

            // revert and try swap with prev
            swap(ord[posInserted], ord[pos2]);
            int pos1 = (posInserted - 1 + m) % m;
            swap(ord[posInserted], ord[pos1]);
            int x3 = ord[pos1];
            int prev3 = ord[(pos1 - 1 + m) % m];
            int next3 = ord[(pos1 + 1) % m];
            int mask3 = ask(prev3, x3, next3);
            bool prev3next3 = inMaskPair(mask3, min(prev3, next3), max(prev3, next3), prev3, x3, next3);
            if (!prev3next3) return true;

            // revert
            swap(ord[posInserted], ord[pos1]);
            return false;
        }
        return true;
    }

    void solve() {
        if (!(cin >> k >> n)) return;

        // Fallback for non-interactive environment
        if (n <= 0) return;

        vector<int> ord;
        ord.reserve(n);
        ord.push_back(0);
        ord.push_back(1);
        ord.push_back(2);

        // Start with an arbitrary cyclic order for first three (always valid up to reflection/rotation).
        for (int x = 3; x < n; x++) {
            int m = (int)ord.size();

            int insertPos = 0;

            if (m <= 18) {
                // Brute window scan over all edges
                int bestScore = -1;
                for (int j = 0; j < m; j++) {
                    int a = ord[j];
                    int b = ord[(j + 1) % m];
                    int mask = ask(a, b, x);
                    bool ab = inMaskPair(mask, a, b, a, b, x);
                    bool ax = inMaskPair(mask, min(a, x), max(a, x), a, b, x);
                    bool bx = inMaskPair(mask, min(b, x), max(b, x), a, b, x);
                    int score = 0;
                    if (!ab) score += 3;
                    if (ax) score += 1;
                    if (bx) score += 1;
                    if (score > bestScore) {
                        bestScore = score;
                        insertPos = j + 1;
                    }
                }
                if (insertPos > m) insertPos %= m;
            } else {
                int cand = pickCandidate(ord, x, 7);
                int idx = findIndex(ord, cand);
                if (idx < 0) idx = 0;
                insertPos = bestEdgeInWindow(ord, x, idx, 10);
            }

            ord.insert(ord.begin() + insertPos, x);

            // Light local fix, if possible within remaining query budget.
            int posInserted = insertPos;
            if (posInserted >= (int)ord.size()) posInserted = 0;
            localCheckAndFix(ord, posInserted);
        }

        cout << "!";
        for (int v : ord) cout << " " << v;
        cout << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    InteractiveSolver solver;
    solver.solve();
    return 0;
}