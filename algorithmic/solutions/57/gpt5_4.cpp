#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // Build the string for querying all nodes once
        // We'll reuse this for all Type 1 queries
        string allNodes;
        {
            ostringstream oss;
            oss << "? 1 " << n;
            for (int i = 1; i <= n; ++i) oss << " " << i;
            allNodes = oss.str();
        }

        auto ask_sum_all = [&]() -> long long {
            cout << allNodes << '\n' << flush;
            long long ans;
            cin >> ans;
            return ans;
        };

        auto toggle = [&](int u) {
            cout << "? 2 " << u << '\n' << flush;
            // No response to read for type 2
        };

        // We'll not toggle node s
        int s = 1;

        vector<long long> sz(n + 1, -1);
        vector<int> a_old(n + 1, 0);

        long long S_prev = ask_sum_all(); // initial baseline
        long long S_curr = S_prev;

        for (int u = 1; u <= n; ++u) {
            if (u == s) continue;
            toggle(u);
            S_curr = ask_sum_all();
            long long delta = S_curr - S_prev; // delta = -2 * a_old(u) * sz(u)
            S_prev = S_curr;

            sz[u] = llabs(delta) / 2;
            a_old[u] = (delta > 0 ? -1 : 1); // since delta = -2 * a_old * sz
        }

        // Compute sz[s]
        bool knownRoot = false;
        for (int u = 1; u <= n; ++u) {
            if (u == s) continue;
            if (sz[u] == n) { knownRoot = true; break; }
        }
        if (!knownRoot) {
            // s is the root
            sz[s] = n;
        } else {
            // s is not the root
            // parent p of s is the neighbor with maximum sz
            int p = -1;
            long long maxsz = -1;
            for (int v : adj[s]) {
                if (sz[v] > maxsz) {
                    maxsz = sz[v];
                    p = v;
                }
            }
            // Find parent of p (if exists): neighbor x of p with sz[x] > sz[p]
            int par_p = -1;
            for (int x : adj[p]) {
                if (x == s) continue; // exclude s (unknown sz)
                if (sz[x] > sz[p]) {
                    par_p = x; break;
                }
            }
            long long sum_children_except_s = 0;
            for (int x : adj[p]) {
                if (x == s) continue;
                if (par_p != -1 && x == par_p) continue;
                sum_children_except_s += sz[x];
            }
            sz[s] = sz[p] - 1 - sum_children_except_s;
        }

        // Compute a_old[s] using S_initial = sum a[u]*sz[u]
        long long sum_known = 0;
        for (int u = 1; u <= n; ++u) {
            if (u == s) continue;
            sum_known += (long long)a_old[u] * sz[u];
        }
        long long numer = S_curr; // S_prev after last operation equals S_curr, but S0 was the initial value.
        // Wait: S_prev is the last S after many toggles; we need S0 (initial baseline)
        // We stored the initial baseline in the first S_prev before loop as 'baseline' effectively.
        // But S_prev was overwritten; However the initial baseline is the first ask_sum_all() stored before loop:
        // That was S_prev before it got updated. We need to keep it separately.
        // To fix, let's track baseline S0 explicitly.
        // Since we cannot edit earlier code lines in this snippet, we can reconstruct:
        // We have:
        // - Initially S_prev0 = initial baseline
        // - After loop, S_prev = S_curr = final
        // We need S0. We can recompute S0 = final - sum of deltas.
        // But we didn't store all deltas; Let's fix: We'll recompute using what we have:
        // The initial baseline S0 was the first value read. We can recompute it by retracing logic:
        // We had S0 stored in the first ask_sum_all() as S_prev then S_curr.
        // However above we overwrote S_prev = S_curr each iteration, and we didn't store S0 long-term.
        // We can fix by tracking S0 separately from the start.
        // To correct the code properly, we will re-run the algorithm from the top inside this block by maintaining S0.
        // Instead of the hack above, we'll adjust the code to store S0.

        // Since we cannot modify already executed code lines, we will restart the whole test case logic cleanly.
        // But we actually can restructure since the program hasn't produced output for this test after this point.
        // Easiest is to wrap per-test-case logic in a lambda and call it. However, in a single stream, we cannot rewind.
        // Therefore, to keep correctness, we will implement the correct logic from scratch below and terminate after printing answer.
        // But we have already sent queries to the interactor, so we must continue with consistent state.
        // The right approach is: we should have stored S0 at start. Let's fix by reading it again:
        // We cannot re-ask S0 without an extra query.
        // Fortunately, we can reconstruct S0 from stored data if we store deltas. We'll recompute deltas retroactively.
        // Let's adjust: We'll redo the loop with stored deltas. But we did not store deltas. However we can store S history: S after each toggle.
        // We'll implement properly below: Restart test with newly read edges is impossible. So to ensure correctness, we'll implement the entire logic again for the next test cases. For this one, we need S0.
        // However, we can compute S0 = sum a[u]*sz[u] using the fact that S_curr (current S) equals S0 + sum(-2 * a_old(u) * sz(u)) over toggled u.
        // We do have S_curr, we also have a_old(u) and sz(u) for all toggled u, so we can solve:
        // S0 = S_curr - sum(-2 * a_old(u) * sz(u)) = S_curr + 2 * sum(a_old(u) * sz(u)).
        // Let's use that.

        // Recompute S0 from current state:
        long long sum_a_sz_toggled = 0;
        for (int u = 1; u <= n; ++u) {
            if (u == s) continue;
            sum_a_sz_toggled += (long long)a_old[u] * sz[u];
        }
        long long S0 = S_curr + 2 * sum_a_sz_toggled;

        sum_known = sum_a_sz_toggled; // same as above
        long long denom = sz[s];
        long long a_s = 0;
        if (denom != 0) {
            long long val = S0 - sum_known;
            // val should be a_s * sz[s]
            if (val % denom == 0) a_s = val / denom;
            else {
                // Fallback: sign by majority (shouldn't happen)
                a_s = (val >= 0 ? 1 : -1);
            }
            if (a_s > 1) a_s = 1;
            if (a_s < -1) a_s = -1;
        } else {
            a_s = 1; // shouldn't happen (size can't be zero), default
        }
        a_old[s] = (int)a_s;

        // Final values after our toggles: all nodes except s were toggled exactly once
        vector<int> a_final(n + 1);
        for (int u = 1; u <= n; ++u) {
            if (u == s) a_final[u] = a_old[u];
            else a_final[u] = -a_old[u];
        }

        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << a_final[i];
        }
        cout << '\n' << flush;
    }
    return 0;
}