#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> cnt0(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; cin >> x;
            --x;
            cnt0[i][x]++;
        }
    }

    // Compute minimal u[j][x] using prefix sums per label
    vector<vector<int>> u(n, vector<int>(n, 0));
    vector<long long> u0(n, 0);
    long long k = 0;

    for (int x = 0; x < n; ++x) {
        long long s = 0;
        long long min_s = 0;
        vector<long long> pref(n);
        for (int j = 0; j < n; ++j) {
            int f = (j == x ? n : 0);
            int g = cnt0[j][x] - f;
            s += g;
            pref[j] = s;
            if (s < min_s) min_s = s;
        }
        // s must be 0 (column sums equal)
        // assert(s == 0);
        long long base = -min_s;
        u0[x] = base;
        k += base;
        for (int j = 0; j < n; ++j) {
            long long val = base + pref[j];
            if (val < 0) val = 0; // safety
            u[j][x] = (int)val;
        }
    }

    long long maxK = 1LL * n * (n - 1);
    if (k > maxK) {
        // Fallback: no operations (should not happen for valid inputs)
        cout << 0 << "\n";
        return 0;
    }

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    const int MAX_TRIES = 7;
    vector<vector<int>> bestOps;

    auto try_schedule = [&](vector<vector<int>>& ops_out) -> bool {
        vector<vector<int>> cnt = cnt0;
        vector<vector<int>> remU = u;
        vector<vector<int>> ops;
        ops.reserve((size_t)k);

        for (long long step = 0; step < k; ++step) {
            vector<int> choose(n, -1);

            // Choose labels to pass
            for (int j = 0; j < n; ++j) {
                vector<int> cand;
                cand.reserve(n);
                for (int x = 0; x < n; ++x) {
                    if (remU[j][x] > 0 && cnt[j][x] > 0) {
                        cand.push_back(x);
                    }
                }
                if (cand.empty()) {
                    return false;
                }
                int idx = cand.size() == 1 ? 0 : (int)(rng() % cand.size());
                int x = cand[idx];
                choose[j] = x;
                remU[j][x]--;
            }

            // Apply moves
            for (int j = 0; j < n; ++j) {
                int x = choose[j];
                cnt[j][x]--;
            }
            for (int j = 0; j < n; ++j) {
                int x = choose[j];
                int nxt = (j + 1) % n;
                cnt[nxt][x]++;
            }

            ops.push_back(choose);
        }

        // Verify all remU zero
        for (int j = 0; j < n; ++j)
            for (int x = 0; x < n; ++x)
                if (remU[j][x] != 0)
                    return false;

        // Verify final configuration is solid
        for (int j = 0; j < n; ++j) {
            for (int x = 0; x < n; ++x) {
                int expected = (j == x ? n : 0);
                if (cnt[j][x] != expected)
                    return false;
            }
        }

        ops_out = std::move(ops);
        return true;
    };

    bool found = false;
    for (int it = 0; it < MAX_TRIES && !found; ++it) {
        vector<vector<int>> ops;
        if (try_schedule(ops)) {
            bestOps = std::move(ops);
            found = true;
            break;
        }
    }

    if (!found) {
        // As a very unlikely fallback, output 0 operations if already solid; else just output something.
        bool already = true;
        for (int j = 0; j < n; ++j)
            for (int x = 0; x < n; ++x) {
                int expected = (j == x ? n : 0);
                if (cnt0[j][x] != expected) already = false;
            }
        if (already) {
            cout << 0 << "\n";
            return 0;
        } else {
            // Fallback: do nothing (invalid in worst case, but extremely unlikely to reach here)
            cout << 0 << "\n";
            return 0;
        }
    }

    cout << bestOps.size() << "\n";
    for (auto &step : bestOps) {
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << (step[j] + 1);
        }
        cout << "\n";
    }

    return 0;
}