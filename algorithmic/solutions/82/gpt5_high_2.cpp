#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto flushout = []() {
        cout.flush();
    };

    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int i, int j) -> int {
        cout << "? " << i << " " << j << "\n";
        flushout();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        return x;
    };

    // Random engine
    mt19937 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, n);

    // Choose a random reference r1
    int r1 = dist(rng);

    vector<int> or1(n + 1, -1);
    // Query r1 against all others
    for (int i = 1; i <= n; ++i) {
        if (i == r1) continue;
        or1[i] = ask(r1, i);
    }

    // Build candidates: those i with minimal or1[i]
    int min1 = INT_MAX;
    vector<int> cand;
    for (int i = 1; i <= n; ++i) {
        if (i == r1) continue;
        if (or1[i] < min1) {
            min1 = or1[i];
            cand.clear();
            cand.push_back(i);
        } else if (or1[i] == min1) {
            cand.push_back(i);
        }
    }

    // Build order (descending by or1) for choosing future references
    vector<int> order;
    order.reserve(n - 1);
    for (int i = 1; i <= n; ++i) if (i != r1) order.push_back(i);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (or1[a] != or1[b]) return or1[a] > or1[b];
        return a < b;
    });

    vector<char> usedRef(n + 1, false);
    usedRef[r1] = true;

    auto isInCand = [&](int x, const vector<int>& v) -> bool {
        for (int y : v) if (y == x) return true;
        return false;
    };

    // Iteratively reduce cand using new references chosen from order
    int ptr = 0;
    while ((int)cand.size() > 1) {
        // pick next reference r not used; prefer outside cand; pick by descending or1
        int r = -1;

        // Try to pick r outside cand first
        while (ptr < (int)order.size()) {
            int candRef = order[ptr++];
            if (usedRef[candRef]) continue;
            if (!isInCand(candRef, cand)) { r = candRef; break; }
        }
        if (r == -1) {
            // If not found, allow picking from cand but make sure it's not used
            for (int x : order) {
                if (!usedRef[x]) { r = x; break; }
            }
        }
        if (r == -1) {
            // As a fallback, pick any not used (including r1 already used; but avoid reusing)
            for (int i = 1; i <= n; ++i) {
                if (!usedRef[i] && i != r1) { r = i; break; }
            }
        }
        if (r == -1) break; // Should not happen

        usedRef[r] = true;

        int minr = INT_MAX;
        vector<int> newCand;
        for (int x : cand) {
            if (x == r) continue; // cannot ask r with itself
            int val = ask(r, x);
            if (val < minr) {
                minr = val;
                newCand.clear();
                newCand.push_back(x);
            } else if (val == minr) {
                newCand.push_back(x);
            }
        }
        // If cand contained only r (rare), we can't ask (r,r). In that case, keep cand as is.
        if (!newCand.empty()) cand.swap(newCand);
        // else leave cand unchanged and continue with another reference
    }

    int zeroIdx = -1;
    if ((int)cand.size() == 1) {
        int c = cand[0];
        // Disambiguate if r1 might be zero
        // Compare ask(c, d) with or1[d] for some d != c, r1
        // If ask(c,d) < or1[d] then c is zero, else if > then r1 is zero.
        // If equal, try another d.
        int verdict = 0; // -1 => r1 zero, +1 => c zero, 0 => unknown yet
        for (int dPick = 0; dPick < n && verdict == 0; ++dPick) {
            int d = order[dPick % order.size()];
            if (d == c || d == r1) continue;
            int v = ask(c, d);
            if (v < or1[d]) verdict = +1;
            else if (v > or1[d]) verdict = -1;
        }
        if (verdict == +1) zeroIdx = c;
        else if (verdict == -1) zeroIdx = r1;
        else {
            // As a last resort, pick random d's
            for (int trials = 0; trials < 64 && verdict == 0; ++trials) {
                int d = dist(rng);
                if (d == c || d == r1) continue;
                int v = ask(c, d);
                if (v < or1[d]) verdict = +1;
                else if (v > or1[d]) verdict = -1;
            }
            if (verdict == +1) zeroIdx = c;
            else if (verdict == -1) zeroIdx = r1;
            else {
                // Default: assume c is zero (extremely unlikely to be wrong)
                zeroIdx = c;
            }
        }
    } else {
        // If cand did not reduce to 1 (extremely unlikely), pick the one with strongest evidence
        // Choose an index z among cand that minimizes the number of times ask(z, j) > or1[j]
        // We'll sample a few j to decide.
        int best = -1, bestScore = INT_MAX;
        for (int z : cand) {
            int score = 0;
            int samples = 0;
            for (int t = 0; t < (int)order.size() && samples < 32; ++t) {
                int j = order[t];
                if (j == z || j == r1) continue;
                int v = ask(z, j);
                if (v > or1[j]) score++;
                samples++;
            }
            if (score < bestScore) {
                bestScore = score;
                best = z;
            }
        }
        zeroIdx = (best == -1 ? cand[0] : best);
    }

    vector<int> ans(n + 1, -1);
    ans[zeroIdx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zeroIdx) continue;
        ans[i] = ask(zeroIdx, i);
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? '\n' : ' ');
    }
    flushout();

    return 0;
}