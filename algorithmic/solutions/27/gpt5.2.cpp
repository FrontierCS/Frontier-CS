#include <bits/stdc++.h>
using namespace std;

static inline int igcd(int a, int b) {
    while (b) { int t = a % b; a = b; b = t; }
    return a;
}

static vector<int> buildSidonMod(int M) {
    if (M <= 1) return {0};

    int upper = (int)(sqrtl((long double)M) + 2.0L);
    upper = min(upper, M);

    int attempts;
    if (M <= 2000) attempts = 30;
    else if (M <= 20000) attempts = 12;
    else attempts = 6;

    mt19937 rng(712367u);

    vector<int> used(M, 0);
    int token = 1;

    vector<int> best;
    best.reserve(upper);

    auto tryAttempt = [&](int start, int step, bool fullCycle) -> vector<int> {
        ++token;
        if (token == INT_MAX) {
            // reset used if token overflows (won't happen here, but keep safe)
            fill(used.begin(), used.end(), 0);
            token = 1;
        }
        vector<int> A;
        A.reserve(upper);
        A.push_back(0);

        auto canAdd = [&](int x) -> bool {
            for (int a : A) {
                int d1 = x - a; if (d1 < 0) d1 += M;
                if (d1 && used[d1] == token) return false;
                int d2 = a - x; if (d2 < 0) d2 += M;
                if (d2 && used[d2] == token) return false;
            }
            return true;
        };

        auto addElem = [&](int x) {
            for (int a : A) {
                int d1 = x - a; if (d1 < 0) d1 += M;
                if (d1) used[d1] = token;
                int d2 = a - x; if (d2 < 0) d2 += M;
                if (d2) used[d2] = token;
            }
            A.push_back(x);
        };

        if (!fullCycle) {
            for (int x = 1; x < M; ++x) {
                if ((int)A.size() >= upper) break;
                if (canAdd(x)) addElem(x);
            }
        } else {
            int cur = start % M;
            for (int cnt = 0; cnt < M; ++cnt) {
                if ((int)A.size() >= upper) break;
                if (cur != 0 && canAdd(cur)) addElem(cur);
                cur += step;
                cur %= M;
            }
        }

        return A;
    };

    // Deterministic attempt first.
    best = tryAttempt(0, 1, false);

    for (int att = 1; att < attempts && (int)best.size() < upper; ++att) {
        int step = uniform_int_distribution<int>(1, M - 1)(rng);
        while (igcd(step, M) != 1) step = uniform_int_distribution<int>(1, M - 1)(rng);
        int start = uniform_int_distribution<int>(0, M - 1)(rng);

        vector<int> A = tryAttempt(start, step, true);
        if (A.size() > best.size()) best.swap(A);
    }

    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<pair<int,int>> ans;

    if (n == 1) {
        ans.reserve(m);
        for (int c = 1; c <= m; ++c) ans.push_back({1, c});
    } else if (m == 1) {
        ans.reserve(n);
        for (int r = 1; r <= n; ++r) ans.push_back({r, 1});
    } else {
        long long k_star = (long long)n + (long long)m - 1;

        int s = min(n, m);
        int M = max(n, m);
        int upper = (int)(sqrtl((long double)M) + 2.0L);
        long long k_sidon_upper = 1LL * s * min(upper, M);

        bool try_sidon = (k_sidon_upper > k_star);

        vector<pair<int,int>> bestStar;
        bestStar.reserve((size_t)k_star);
        // Star: full row 1 + first column (rows 2..n)
        for (int c = 1; c <= m; ++c) bestStar.push_back({1, c});
        for (int r = 2; r <= n; ++r) bestStar.push_back({r, 1});

        ans = std::move(bestStar);

        if (try_sidon) {
            vector<int> A = buildSidonMod(M);
            long long k_sidon = 1LL * s * (int)A.size();

            if (k_sidon > (long long)ans.size()) {
                vector<pair<int,int>> sidonAns;
                sidonAns.reserve((size_t)k_sidon);

                if (n <= m) {
                    // rows are shifts, columns modulo m
                    for (int r = 1; r <= n; ++r) {
                        int shift = r - 1;
                        for (int a : A) {
                            int c = (shift + a) % m + 1;
                            sidonAns.push_back({r, c});
                        }
                    }
                } else {
                    // columns are shifts, rows modulo n
                    for (int c = 1; c <= m; ++c) {
                        int shift = c - 1;
                        for (int a : A) {
                            int r = (shift + a) % n + 1;
                            sidonAns.push_back({r, c});
                        }
                    }
                }

                ans.swap(sidonAns);
            }
        }
    }

    cout << ans.size() << "\n";
    for (auto &p : ans) cout << p.first << " " << p.second << "\n";
    return 0;
}