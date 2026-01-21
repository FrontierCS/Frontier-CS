#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using i128 = __int128_t;

ll mod_pow(ll a, ll e, ll mod) {
    i128 r = 1, b = a % mod;
    while (e) {
        if (e & 1) r = (r * b) % mod;
        b = (b * b) % mod;
        e >>= 1;
    }
    return (ll)r;
}

ll mod_inv(ll a, ll mod) {
    return mod_pow((a % mod + mod) % mod, mod - 2, mod);
}

// Solve linear system A * x = b over modulo 'mod'.
// A: n x m, b: length n, solution x: length m.
// Returns false if no solution.
bool gauss_mod(const vector<vector<int>> &C, int n, int m, ll mod, vector<ll> &x) {
    vector<vector<ll>> a(n, vector<ll>(m + 1));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            a[i][j] = (C[i][j + 1] % (int)mod + mod) % mod;
        }
        a[i][m] = 1 % mod; // RHS is all ones
    }

    vector<int> where(m, -1);
    int row = 0;
    for (int col = 0; col < m && row < n; ++col) {
        int sel = row;
        while (sel < n && a[sel][col] == 0) ++sel;
        if (sel == n) continue;
        swap(a[sel], a[row]);
        where[col] = row;

        ll inv_pivot = mod_inv(a[row][col], mod);
        for (int j = col; j <= m; ++j) {
            a[row][j] = (a[row][j] * inv_pivot) % mod;
        }
        for (int i = 0; i < n; ++i) {
            if (i != row && a[i][col] != 0) {
                ll factor = a[i][col];
                for (int j = col; j <= m; ++j) {
                    a[i][j] = (a[i][j] - factor * a[row][j]) % mod;
                    if (a[i][j] < 0) a[i][j] += mod;
                }
            }
        }
        ++row;
    }

    // Check for inconsistency
    for (int i = 0; i < n; ++i) {
        bool allZero = true;
        for (int j = 0; j < m; ++j) {
            if (a[i][j] != 0) {
                allZero = false;
                break;
            }
        }
        if (allZero && a[i][m] != 0) return false;
    }

    x.assign(m, 0);
    for (int j = 0; j < m; ++j) {
        if (where[j] != -1) x[j] = a[where[j]][m];
        else x[j] = 0;
    }
    return true;
}

// Solve A * x = b over reals (long double) for approximation.
bool gauss_double(const vector<vector<int>> &C, int n, int m, vector<long double> &x) {
    vector<vector<long double>> a(n, vector<long double>(m + 1));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            a[i][j] = (long double)C[i][j + 1];
        }
        a[i][m] = 1.0L; // RHS ones
    }

    const long double EPS = 1e-12L;
    vector<int> where(m, -1);
    int row = 0;
    for (int col = 0; col < m && row < n; ++col) {
        int sel = row;
        for (int i = row; i < n; ++i) {
            if (fabsl(a[i][col]) > fabsl(a[sel][col])) sel = i;
        }
        if (fabsl(a[sel][col]) < EPS) continue;
        swap(a[sel], a[row]);
        where[col] = row;

        long double pivot = a[row][col];
        for (int j = col; j <= m; ++j) a[row][j] /= pivot;

        for (int i = 0; i < n; ++i) {
            if (i != row && fabsl(a[i][col]) > EPS) {
                long double factor = a[i][col];
                for (int j = col; j <= m; ++j) {
                    a[i][j] -= factor * a[row][j];
                }
            }
        }
        ++row;
    }

    for (int i = 0; i < n; ++i) {
        bool allZero = true;
        for (int j = 0; j < m; ++j) {
            if (fabsl(a[i][j]) > EPS) {
                allZero = false;
                break;
            }
        }
        if (allZero && fabsl(a[i][m]) > EPS) return false;
    }

    x.assign(m, 0.0L);
    for (int j = 0; j < m; ++j) {
        if (where[j] != -1) x[j] = a[where[j]][m];
        else x[j] = 0.0L;
    }
    return true;
}

// CRT for two congruences: x ≡ r1 (mod p1), x ≡ r2 (mod p2).
ll crt2(ll r1, ll p1, ll r2, ll p2) {
    ll m1 = p1, m2 = p2;
    ll inv = mod_inv(m1 % m2, m2);
    ll t = (ll)((i128)((((r2 - r1) % m2) + m2) % m2) * inv % m2);
    i128 x = (i128)r1 + (i128)m1 * t;
    return (ll)x; // x in [0, p1*p2)
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    int H = h;
    int Dmax = 2 * (h - 1);
    int N = (1 << h) - 1;

    // Build tree adjacency
    vector<vector<int>> adj(N + 1);
    for (int i = 2; i <= N; ++i) {
        int p = i / 2;
        adj[i].push_back(p);
        adj[p].push_back(i);
    }

    // Precompute C[k][d]: k = depth (0..H-1), d = distance (1..Dmax)
    vector<vector<int>> C(H, vector<int>(Dmax + 1, 0));
    vector<int> dist(N + 1);
    vector<int> q(N + 1);

    for (int k = 0; k < H; ++k) {
        int start = 1 << k;
        fill(dist.begin(), dist.end(), -1);
        int head = 0, tail = 0;
        q[tail++] = start;
        dist[start] = 0;
        while (head < tail) {
            int v = q[head++];
            int dv = dist[v];
            for (int to : adj[v]) {
                if (dist[to] == -1) {
                    dist[to] = dv + 1;
                    q[tail++] = to;
                }
            }
        }
        vector<int> freq(Dmax + 1, 0);
        for (int v = 1; v <= N; ++v) {
            int d = dist[v];
            if (d >= 1 && d <= Dmax) ++freq[d];
        }
        for (int d = 1; d <= Dmax; ++d) C[k][d] = freq[d];
    }

    int nEq = H;
    int nVar = Dmax;

    // Candidate primes
    vector<ll> candPrimes = {
        1000000007LL, 1000000009LL, 1000000033LL,
        1000000087LL, 1000000093LL, 1000000097LL,
        1000000103LL
    };

    struct ModInfo {
        ll p;
        vector<ll> alpha;      // size Dmax, coefficients for each distance d (1..Dmax)
        vector<ll> Tmod;       // accumulated sums per distance
    };
    vector<ModInfo> mods;

    // Solve C * alpha = 1 over each modulus
    for (ll p : candPrimes) {
        vector<ll> alpha;
        if (gauss_mod(C, nEq, nVar, p, alpha)) {
            ModInfo mi;
            mi.p = p;
            mi.alpha = std::move(alpha);
            mi.Tmod.assign(Dmax + 1, 0); // index by d (1..Dmax)
            mods.push_back(std::move(mi));
        }
    }

    // Approximate solution over reals
    vector<long double> alphaD;
    bool haveDouble = gauss_double(C, nEq, nVar, alphaD);

    // Accumulate total sums per distance
    vector<i128> Ttot(Dmax + 1);
    for (int d = 1; d <= Dmax; ++d) Ttot[d] = 0;

    // Interactive queries: for each distance d, query all centers u
    for (int d = 1; d <= Dmax; ++d) {
        for (int u = 1; u <= N; ++u) {
            cout << "? " << u << " " << d << endl;
            cout.flush();
            ll ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0; // in case of judge error signal
            Ttot[d] += (i128)ans;
            for (auto &mi : mods) {
                ll mod = mi.p;
                mi.Tmod[d] += ans % mod;
                if (mi.Tmod[d] >= mod) mi.Tmod[d] -= mod;
            }
        }
    }

    ll finalS = 0;
    bool exact = false;

    if (mods.size() >= 2) {
        // Use first two good primes and CRT for exact result
        auto &m1 = mods[0];
        auto &m2 = mods[1];
        ll p1 = m1.p, p2 = m2.p;

        ll s1 = 0, s2 = 0;
        for (int j = 0; j < nVar; ++j) {
            int d = j + 1;
            ll coef1 = m1.alpha[j] % p1;
            ll coef2 = m2.alpha[j] % p2;
            if (coef1 < 0) coef1 += p1;
            if (coef2 < 0) coef2 += p2;
            if (coef1) {
                s1 = (s1 + coef1 * (m1.Tmod[d] % p1)) % p1;
            }
            if (coef2) {
                s2 = (s2 + coef2 * (m2.Tmod[d] % p2)) % p2;
            }
        }
        if (s1 < 0) s1 += p1;
        if (s2 < 0) s2 += p2;
        ll x = crt2(s1, p1, s2, p2);
        finalS = x;
        exact = true;
    } else if (mods.size() == 1) {
        // One modulus + approximate real solution
        auto &m1 = mods[0];
        ll p1 = m1.p;
        ll s1 = 0;
        for (int j = 0; j < nVar; ++j) {
            int d = j + 1;
            ll coef1 = m1.alpha[j] % p1;
            if (coef1 < 0) coef1 += p1;
            if (coef1) {
                s1 = (s1 + coef1 * (m1.Tmod[d] % p1)) % p1;
            }
        }
        if (s1 < 0) s1 += p1;

        long long approxInt = 0;
        if (haveDouble) {
            long double approx = 0.0L;
            for (int j = 0; j < nVar; ++j) {
                int d = j + 1;
                long double td = (long double)Ttot[d];
                approx += alphaD[j] * td;
            }
            approxInt = (long long)llround(approx);
        }

        const long long RANGE = 2000000LL; // search window
        long long best = -1;
        for (long long delta = -RANGE; delta <= RANGE; ++delta) {
            long long cand = approxInt + delta;
            if (cand < 0) continue;
            if ((cand % p1 + p1) % p1 == s1) {
                best = cand;
                break;
            }
        }
        if (best == -1) {
            best = approxInt;
        }
        finalS = best;
        exact = true; // assume good enough
    } else {
        // No modular solutions; fall back purely to double
        if (haveDouble) {
            long double approx = 0.0L;
            for (int j = 0; j < nVar; ++j) {
                int d = j + 1;
                long double td = (long double)Ttot[d];
                approx += alphaD[j] * td;
            }
            finalS = (long long)llround(approx);
        } else {
            // As a last resort (should not happen), output 0
            finalS = 0;
        }
    }

    cout << "! " << finalS << endl;
    cout.flush();
    return 0;
}