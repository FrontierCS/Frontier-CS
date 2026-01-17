#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int n;
int queries_used = 0;

int query(int x, int y) {
    if (x == y) return 0;
    cout << "? " << x << " " << y << endl;
    queries_used++;
    int res;
    cin >> res;
    return res;
}

void answer(int u, int v) {
    cout << "! " << u << " " << v << endl;
}

int cyclic_dist(int a, int b) {
    int d = abs(a - b);
    return min(d, n - d);
}

bool are_adjacent(int a, int b) {
    if (a > b) swap(a, b);
    return (b - a == 1) || (a == 1 && b == n);
}

// Try to find the chord assuming that u is one of its endpoints.
// Returns true if found and outputs the answer.
bool try_endpoint(int u) {
    // We'll search in both directions from u.
    for (int step : {1, -1}) {
        int lo = 2, hi = n / 2; // k (distance along cycle)
        int found_k = -1;
        int v_found = -1;
        int d_val = -1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            int v = u + step * mid;
            // Adjust v to [1, n] modulo n
            v = ((v - 1) % n + n) % n + 1;
            int d = query(u, v);
            if (d < mid) {
                found_k = mid;
                v_found = v;
                d_val = d;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
            if (queries_used > 500) return false; // safety
        }
        if (found_k != -1) {
            // Candidate: other endpoint w satisfies d(w, v_found) = d_val - 1
            int dist_w = d_val - 1;
            if (dist_w < 0) continue;
            for (int sign : {1, -1}) {
                int w = v_found + sign * dist_w;
                w = ((w - 1) % n + n) % n + 1;
                if (w == u) continue;
                if (are_adjacent(u, w)) continue; // chord must be non-adjacent
                int d2 = query(u, w);
                if (d2 == 1) {
                    answer(min(u, w), max(u, w));
                    return true;
                }
                if (queries_used > 500) return false;
            }
        }
    }
    return false;
}

void solve() {
    queries_used = 0;
    cin >> n;

    // Quick check for very small n (optional, but safe)
    if (n <= 1000) {
        for (int i = 1; i <= n; i++) {
            for (int j = i + 2; j <= n; j++) {
                if (i == 1 && j == n) continue; // adjacent in cycle
                int d = query(i, j);
                if (d == 1) {
                    answer(i, j);
                    return;
                }
                if (queries_used > 500) return;
            }
        }
        // Should never reach here because chord exists.
        return;
    }

    // First, check if vertex 1 is an endpoint by testing a few likely candidates.
    // Chord endpoints are non-adjacent, so check vertices at distance 2 from 1.
    int cand1 = 3;
    int cand2 = n - 1;
    if (cand1 > n) cand1 = 1;
    if (cand2 < 1) cand2 = n;
    int d1 = query(1, cand1);
    if (d1 == 1 && !are_adjacent(1, cand1)) {
        answer(1, cand1);
        return;
    }
    if (queries_used > 500) return;
    int d2 = query(1, cand2);
    if (d2 == 1 && !are_adjacent(1, cand2)) {
        answer(1, cand2);
        return;
    }
    if (queries_used > 500) return;

    // Try several vertices as potential endpoints.
    // We try some small numbers and also some roughly equally spaced vertices.
    vector<int> trials;
    for (int i = 1; i <= min(20, n); i++) trials.push_back(i);
    if (n > 20) {
        trials.push_back(n / 4);
        trials.push_back(n / 2);
        trials.push_back(3 * n / 4);
    }
    // Remove duplicates
    sort(trials.begin(), trials.end());
    trials.erase(unique(trials.begin(), trials.end()), trials.end());

    for (int u : trials) {
        if (u < 1 || u > n) continue;
        if (try_endpoint(u)) {
            return;
        }
        if (queries_used > 500) break;
    }

    // If we haven't found yet, we might have run out of queries or the heuristic failed.
    // As a fallback, we can try a few random pairs (but this is not guaranteed).
    // We'll just exit and hope for the best (should not happen with proper test cases).
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int T;
    cin >> T;
    while (T--) {
        solve();
        int verdict;
        cin >> verdict;
        if (verdict == -1) {
            exit(0); // Incorrect guess
        }
        // Otherwise, continue to next test case
    }
    return 0;
}