#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ull = unsigned long long;

inline ll llabsll(ll x) { return x >= 0 ? x : -x; }

inline bool getBit(const vector<ull>& v, int pos) {
    return (v[pos >> 6] >> (pos & 63)) & 1ULL;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    ll T;
    if (!(cin >> n >> T)) return 0;
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    ll sumAll = 0;
    for (int i = 0; i < n; ++i) sumAll += a[i];

    // Edge case: all zeros
    if (sumAll == 0) {
        string res(n, '0');
        cout << res << '\n';
        return 0;
    }

    // Approximate DP with scaling
    const int MAX_S_TARGET = 2000000; // target max scaled sum

    ll s;
    if (sumAll <= MAX_S_TARGET) s = 1;
    else s = (sumAll + MAX_S_TARGET - 1) / MAX_S_TARGET; // ceil

    vector<ll> w(n);
    ll S = 0;
    for (int i = 0; i < n; ++i) {
        // nearest integer rounding
        w[i] = (a[i] + s / 2) / s;
        if (w[i] < 0) w[i] = 0;
        S += w[i];
    }
    int S_int = (int)S;
    int words = (S_int >> 6) + 1;

    vector<vector<ull>> dp(n + 1, vector<ull>(words));
    dp[0][0] = 1ULL; // sum 0 reachable

    for (int i = 1; i <= n; ++i) {
        const auto& prev = dp[i - 1];
        auto& cur = dp[i];
        // copy previous
        for (int k = 0; k < words; ++k) cur[k] = prev[k];

        int shiftBits = (int)w[i - 1];
        if (shiftBits > 0) {
            int whole = shiftBits >> 6;
            int part = shiftBits & 63;
            for (int j = 0; j < words; ++j) {
                ull v = prev[j];
                if (!v) continue;
                int di = j + whole;
                if (di >= words) break;
                if (part == 0) {
                    cur[di] |= v;
                } else {
                    cur[di] |= v << part;
                    if (di + 1 < words)
                        cur[di + 1] |= v >> (64 - part);
                }
            }
        }
    }

    // Target in scaled space
    ll TwScaled_ll = (T + s / 2) / s;
    if (TwScaled_ll < 0) TwScaled_ll = 0;
    if (TwScaled_ll > S_int) TwScaled_ll = S_int;
    int TwScaled = (int)TwScaled_ll;

    const auto& last = dp[n];
    int bestW = -1;
    for (int d = 0; d <= S_int; ++d) {
        int s1 = TwScaled - d;
        if (s1 >= 0 && getBit(last, s1)) {
            bestW = s1;
            break;
        }
        int s2 = TwScaled + d;
        if (s2 <= S_int && getBit(last, s2)) {
            bestW = s2;
            break;
        }
    }
    if (bestW == -1) bestW = 0; // fallback, though shouldn't happen

    // Reconstruct one subset for scaled sum bestW
    vector<int> takeDP(n, 0);
    int curW = bestW;
    for (int i = n; i >= 1; --i) {
        int wi = (int)w[i - 1];
        if (curW >= wi && getBit(dp[i - 1], curW - wi)) {
            takeDP[i - 1] = 1;
            curW -= wi;
        } else {
            takeDP[i - 1] = 0;
        }
    }

    auto computeSum = [&](const vector<int>& take) -> ll {
        ll ssum = 0;
        for (int i = 0; i < n; ++i)
            if (take[i]) ssum += a[i];
        return ssum;
    };

    // Local search (1-flip and 2-flip hill climbing)
    auto hillClimb = [&](vector<int>& take, ll& curSum) {
        while (true) {
            bool improved = false;
            ll curErr = llabsll(curSum - T);

            // Best 1-bit flip
            ll bestDelta = 0;
            int bestIdx = -1;
            for (int i = 0; i < n; ++i) {
                ll newSum = curSum + (take[i] ? -a[i] : a[i]);
                ll newErr = llabsll(newSum - T);
                ll delta = curErr - newErr;
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestIdx = i;
                }
            }
            if (bestIdx != -1) {
                if (take[bestIdx]) curSum -= a[bestIdx];
                else curSum += a[bestIdx];
                take[bestIdx] ^= 1;
                improved = true;
            } else {
                // Try 2-bit flips
                ll bestDelta2 = 0;
                int bi = -1, bj = -1;
                for (int i = 0; i < n; ++i) {
                    for (int j = i + 1; j < n; ++j) {
                        ll newSum = curSum
                                    + (take[i] ? -a[i] : a[i])
                                    + (take[j] ? -a[j] : a[j]);
                        ll newErr = llabsll(newSum - T);
                        ll delta = curErr - newErr;
                        if (delta > bestDelta2) {
                            bestDelta2 = delta;
                            bi = i;
                            bj = j;
                        }
                    }
                }
                if (bestDelta2 > 0) {
                    if (take[bi]) curSum -= a[bi];
                    else curSum += a[bi];
                    take[bi] ^= 1;
                    if (take[bj]) curSum -= a[bj];
                    else curSum += a[bj];
                    take[bj] ^= 1;
                    improved = true;
                }
            }

            if (!improved) break;
        }
    };

    vector<int> bestSol(n, 0);
    bool bestInit = false;
    ll bestErr = 0;
    ll bestSum = 0;

    auto considerSolution = [&](vector<int> sol) {
        ll sum = computeSum(sol);
        hillClimb(sol, sum);
        ll err = llabsll(sum - T);
        if (!bestInit || err < bestErr) {
            bestInit = true;
            bestErr = err;
            bestSol = std::move(sol);
            bestSum = sum;
        }
    };

    // Seed 1: DP-based solution
    considerSolution(takeDP);

    // Seed 2: Greedy from zero (add in descending order)
    {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int i, int j) {
            return a[i] > a[j];
        });
        vector<int> greedy(n, 0);
        ll sum = 0;
        ll err = llabsll(sum - T);
        for (int id : idx) {
            ll nsum = sum + a[id];
            ll nerr = llabsll(nsum - T);
            if (nerr <= err) {
                greedy[id] = 1;
                sum = nsum;
                err = nerr;
            }
        }
        considerSolution(greedy);
    }

    // Seed 3: Greedy from all ones (remove in ascending order)
    {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int i, int j) {
            return a[i] < a[j];
        });
        vector<int> greedy(n, 1);
        ll sum = sumAll;
        ll err = llabsll(sum - T);
        for (int id : idx) {
            ll nsum = sum - a[id];
            ll nerr = llabsll(nsum - T);
            if (nerr <= err) {
                greedy[id] = 0;
                sum = nsum;
                err = nerr;
            }
        }
        considerSolution(greedy);
    }

    // A few random seeds
    {
        mt19937_64 rng((ull)chrono::steady_clock::now().time_since_epoch().count());
        int randomRuns = 3;
        for (int r = 0; r < randomRuns; ++r) {
            vector<int> rnd(n);
            for (int i = 0; i < n; ++i) rnd[i] = (rng() & 1ULL) ? 1 : 0;
            considerSolution(rnd);
        }
    }

    // Output best solution
    string out;
    out.reserve(n);
    for (int i = 0; i < n; ++i) out.push_back(bestSol[i] ? '1' : '0');
    cout << out << '\n';

    return 0;
}