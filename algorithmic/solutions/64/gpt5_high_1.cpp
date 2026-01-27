#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Solver {
    int n;
    ll T;
    vector<ll> a;
    mt19937_64 rng;
    chrono::steady_clock::time_point start;
    long long timeLimitMicros;

    vector<char> bestPick;
    ll bestSum = 0;
    ll bestErr = (1LL<<62);

    inline bool timeExceeded() const {
        auto now = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::microseconds>(now - start).count();
        return elapsed > timeLimitMicros;
    }

    inline ll err(ll S) const {
        ll d = T - S;
        return d >= 0 ? d : -d;
    }

    void updateBest(const vector<char>& pick, ll S) {
        ll e = err(S);
        if (e < bestErr) {
            bestErr = e;
            bestSum = S;
            bestPick = pick;
        }
    }

    void greedy_by_order(const vector<int>& order, vector<char>& pick, ll& S) {
        pick.assign(n, 0);
        S = 0;
        for (int id : order) {
            ll newS = S + a[id];
            if (err(newS) < err(S)) {
                pick[id] = 1;
                S = newS;
            }
        }
    }

    bool one_opt(vector<char>& pick, ll& S) {
        bool improved = false;
        while (!timeExceeded()) {
            ll bestNewErr = err(S);
            int bestIdx = -1;
            ll currentErr = bestNewErr;
            for (int i = 0; i < n; ++i) {
                if (a[i] == 0) continue;
                ll newS = pick[i] ? (S - a[i]) : (S + a[i]);
                ll e = err(newS);
                if (e < bestNewErr) {
                    bestNewErr = e;
                    bestIdx = i;
                }
            }
            if (bestIdx != -1 && bestNewErr < currentErr) {
                if (pick[bestIdx]) S -= a[bestIdx];
                else S += a[bestIdx];
                pick[bestIdx] ^= 1;
                improved = true;
            } else break;
        }
        return improved;
    }

    bool pair_swap(vector<char>& pick, ll& S) {
        ll d = T - S;
        ll currentErr = d >= 0 ? d : -d;
        vector<int> sel, nosel;
        sel.reserve(n);
        nosel.reserve(n);
        for (int i = 0; i < n; ++i) {
            if (pick[i]) sel.push_back(i);
            else nosel.push_back(i);
        }
        if (sel.empty() || nosel.empty()) return false;
        vector<pair<ll,int>> ns;
        ns.reserve(nosel.size());
        for (int j : nosel) ns.emplace_back(a[j], j);
        sort(ns.begin(), ns.end());
        vector<ll> nsVals;
        nsVals.reserve(ns.size());
        for (auto &p : ns) nsVals.push_back(p.first);

        ll bestNewErr = currentErr;
        int bi = -1, bj = -1;

        for (int i : sel) {
            if (timeExceeded()) break;
            ll target = d + a[i];
            auto it = lower_bound(nsVals.begin(), nsVals.end(), target);
            if (it != nsVals.end()) {
                ll e = llabs(target - *it);
                if (e < bestNewErr) {
                    bestNewErr = e;
                    bi = i;
                    bj = ns[it - nsVals.begin()].second;
                }
            }
            if (it != nsVals.begin()) {
                --it;
                ll e = llabs(target - *it);
                if (e < bestNewErr) {
                    bestNewErr = e;
                    bi = i;
                    bj = ns[it - nsVals.begin()].second;
                }
            }
        }
        if (bi != -1 && bj != -1 && bestNewErr < currentErr) {
            pick[bi] = 0;
            pick[bj] = 1;
            S = S - a[bi] + a[bj];
            return true;
        }
        return false;
    }

    bool two_add_remove(vector<char>& pick, ll& S) {
        ll d = T - S;
        ll currentErr = d >= 0 ? d : -d;
        if (currentErr == 0) return false;

        if (d > 0) {
            vector<int> nosel;
            nosel.reserve(n);
            for (int i = 0; i < n; ++i) if (!pick[i]) nosel.push_back(i);
            int m = (int)nosel.size();
            if (m < 2) return false;
            ll bestNewErr = currentErr;
            int b1 = -1, b2 = -1;
            for (int ii = 0; ii < m; ++ii) {
                if (timeExceeded()) break;
                int i = nosel[ii];
                for (int jj = ii + 1; jj < m; ++jj) {
                    int j = nosel[jj];
                    ll sum2 = a[i] + a[j];
                    ll e = llabs(d - sum2);
                    if (e < bestNewErr) {
                        bestNewErr = e;
                        b1 = i; b2 = j;
                    }
                }
            }
            if (b1 != -1 && b2 != -1 && bestNewErr < currentErr) {
                pick[b1] = pick[b2] = 1;
                S += a[b1] + a[b2];
                return true;
            }
        } else {
            vector<int> sel;
            sel.reserve(n);
            for (int i = 0; i < n; ++i) if (pick[i]) sel.push_back(i);
            int m = (int)sel.size();
            if (m < 2) return false;
            ll bestNewErr = currentErr;
            int b1 = -1, b2 = -1;
            for (int ii = 0; ii < m; ++ii) {
                if (timeExceeded()) break;
                int i = sel[ii];
                for (int jj = ii + 1; jj < m; ++jj) {
                    int j = sel[jj];
                    ll sum2 = a[i] + a[j];
                    ll e = llabs(d + sum2);
                    if (e < bestNewErr) {
                        bestNewErr = e;
                        b1 = i; b2 = j;
                    }
                }
            }
            if (b1 != -1 && b2 != -1 && bestNewErr < currentErr) {
                pick[b1] = pick[b2] = 0;
                S -= a[b1] + a[b2];
                return true;
            }
        }
        return false;
    }

    void random_shake(vector<char>& pick, ll& S, int flips = 2) {
        uniform_int_distribution<int> dist(0, n - 1);
        for (int t = 0; t < flips; ++t) {
            int i = dist(rng);
            if (pick[i]) {
                pick[i] = 0;
                S -= a[i];
            } else {
                pick[i] = 1;
                S += a[i];
            }
        }
    }

    void improve(vector<char>& pick, ll& S) {
        one_opt(pick, S);
        while (!timeExceeded()) {
            bool any = false;
            if (pair_swap(pick, S)) {
                any = true;
                one_opt(pick, S);
            } else if (two_add_remove(pick, S)) {
                any = true;
                one_opt(pick, S);
            }
            if (!any) break;
        }
    }

    void run() {
        bestPick.assign(n, 0);
        bestSum = 0;
        bestErr = err(0);

        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);

        // Initial heuristics
        vector<vector<int>> orders;

        // Descending values
        {
            auto id = idx;
            sort(id.begin(), id.end(), [&](int i, int j){ return a[i] > a[j]; });
            orders.push_back(move(id));
        }
        // Ascending values
        {
            auto id = idx;
            sort(id.begin(), id.end(), [&](int i, int j){ return a[i] < a[j]; });
            orders.push_back(move(id));
        }
        // Close to T/n first
        {
            auto id = idx;
            long double avg = (n > 0 ? (long double)T / (long double)max(1, n) : 0.0L);
            sort(id.begin(), id.end(), [&](int i, int j){
                long double di = fabsl((long double)a[i] - avg);
                long double dj = fabsl((long double)a[j] - avg);
                if (di == dj) return a[i] < a[j];
                return di < dj;
            });
            orders.push_back(move(id));
        }
        // A couple of random orders
        for (int r = 0; r < 3; ++r) {
            auto id = idx;
            shuffle(id.begin(), id.end(), rng);
            orders.push_back(move(id));
        }

        vector<char> pick(n, 0);
        ll S = 0;

        for (auto& order : orders) {
            if (timeExceeded()) break;
            greedy_by_order(order, pick, S);
            improve(pick, S);
            updateBest(pick, S);
        }

        // Random restarts until time
        while (!timeExceeded()) {
            // Random greedy order
            auto id = idx;
            shuffle(id.begin(), id.end(), rng);
            greedy_by_order(id, pick, S);
            improve(pick, S);
            updateBest(pick, S);

            if (timeExceeded()) break;

            // Random initial subset
            pick.assign(n, 0);
            S = 0;
            for (int i = 0; i < n; ++i) {
                if ((rng() & 1)) { pick[i] = 1; S += a[i]; }
            }
            improve(pick, S);
            updateBest(pick, S);

            if (timeExceeded()) break;

            // Attempt shaking from best
            pick = bestPick;
            S = bestSum;
            random_shake(pick, S, 2);
            improve(pick, S);
            updateBest(pick, S);
        }
    }

    string solve() {
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
        start = chrono::steady_clock::now();
        // Time limit in microseconds (adjust as needed)
        timeLimitMicros = 1500000; // 1.5 seconds
        run();
        string res;
        res.resize(n);
        for (int i = 0; i < n; ++i) res[i] = bestPick[i] ? '1' : '0';
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    Solver solver;
    solver.n = n;
    solver.T = T;
    solver.a = a;
    string ans = solver.solve();
    cout << ans << "\n";
    return 0;
}