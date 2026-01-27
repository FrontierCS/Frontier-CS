#include <bits/stdc++.h>
using namespace std;

static bool isPrime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * 1LL * i <= x; ++i)
        if (x % i == 0) return false;
    return true;
}

static long long ipow(long long a, int e) {
    long long r = 1;
    while (e--) r *= a;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;

    // Find parameters q (prime), l, t such that:
    // - l <= q
    // - q * l <= R
    // - t = floor((l - 1) / 2)
    // - q^(t+1) >= N
    // Choose minimal q*l to minimize robots used.
    int best_q = -1, best_l = -1, best_t = -1, best_prod = INT_MAX;
    for (int q = 2; q <= R; ++q) {
        if (!isPrime(q)) continue;
        int max_l = min(q, R / q);
        for (int l = max_l; l >= 1; --l) {
            int t = (l - 1) / 2;
            if (t < 0) continue;
            long long cap = ipow(q, t + 1);
            if (cap >= N && l >= 1) {
                int prod = q * l;
                if (prod < best_prod) {
                    best_prod = prod;
                    best_q = q;
                    best_l = l;
                    best_t = t;
                }
            }
        }
    }
    // Fallback to a known good configuration if search fails (shouldn't for R=75, H=1).
    if (best_q == -1) {
        // Use q=7, l=7, t=3 requiring 49 robots (fits R>=49).
        best_q = 7; best_l = 7; best_t = 3; best_prod = best_q * best_l;
        if (best_prod > R) { // final fallback
            best_q = 11; best_l = 6; best_t = 2; best_prod = best_q * best_l;
        }
    }

    int q = best_q, l = best_l, t = best_t;
    // Evaluation points x_j in GF(q), choose 0..l-1
    vector<int> eval_points(l);
    for (int j = 0; j < l; ++j) eval_points[j] = j % q;

    // Map positions 1..N to polynomials of degree <= t over GF(q).
    // Use coefficients as base-q digits: a0 + a1 X + ... + at X^t
    vector<vector<int>> coeffs(N, vector<int>(t + 1, 0));
    for (int id = 0; id < N; ++id) {
        int x = id;
        for (int d = 0; d <= t; ++d) {
            coeffs[id][d] = x % q;
            x /= q;
        }
    }

    auto evalPoly = [&](const vector<int>& c, int xval) -> int {
        long long res = 0;
        long long powx = 1;
        for (int d = 0; d <= t; ++d) {
            res = (res + c[d] * powx) % q;
            powx = (powx * xval) % q;
        }
        return (int)res;
    };

    // Prepare sets for each robot: rows indexed by (block j, value v)
    int rows = l * q;
    vector<vector<int>> sets(rows);
    for (int id = 0; id < N; ++id) {
        for (int j = 0; j < l; ++j) {
            int v = evalPoly(coeffs[id], eval_points[j]);
            int r = j * q + v;
            sets[r].push_back(id + 1); // positions are 1-based
        }
    }

    // Send queries
    for (int r = 0; r < rows; ++r) {
        cout << "? " << sets[r].size();
        for (int pos : sets[r]) cout << " " << pos;
        cout << "\n" << flush;
    }

    // Get answers
    cout << "@\n" << flush;
    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Build availability matrix per block and value
    vector<vector<int>> yblock(l, vector<int>(q, 0));
    for (int j = 0; j < l; ++j) {
        for (int v = 0; v < q; ++v) {
            int idx = j * q + v;
            if (idx < (int)ans.size()) yblock[j][v] = ans[idx];
        }
    }

    // Decode: select positions whose codeword is subset of union (i.e., all blocks present)
    vector<int> candidates;
    for (int id = 0; id < N; ++id) {
        bool ok = true;
        for (int j = 0; j < l; ++j) {
            int v = evalPoly(coeffs[id], eval_points[j]);
            if (v < 0 || v >= q || yblock[j][v] == 0) {
                ok = false; break;
            }
        }
        if (ok) candidates.push_back(id + 1);
        if ((int)candidates.size() > 2) break; // safety
    }

    int a = 1, b = 1;
    if (candidates.size() == 1) {
        a = b = candidates[0];
    } else if (candidates.size() >= 2) {
        a = candidates[0];
        b = candidates[1];
    }

    cout << "! " << a << " " << b << "\n" << flush;
    return 0;
}