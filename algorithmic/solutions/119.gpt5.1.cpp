#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

long long mod_pow(long long a, long long e) {
    long long r = 1 % MOD;
    a %= MOD;
    while (e > 0) {
        if (e & 1) r = (r * a) % MOD;
        a = (a * a) % MOD;
        e >>= 1;
    }
    return r;
}

long long mod_inv(long long x) {
    return mod_pow(x, MOD - 2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const long long a0 = 3;  // value for a_0
    const long long z  = 2;  // fixed value for a_n (n >= 1)

    vector<long long> curr_vals(n + 1);
    curr_vals[0] = a0;
    if (n >= 2) {
        for (int i = 1; i <= n - 1; ++i) curr_vals[i] = 1;
    } else {
        // n == 1: only a0 and a1
    }
    curr_vals[n] = z;

    // Query 0 (baseline)
    cout << "?";
    for (int i = 0; i <= n; ++i) {
        cout << ' ' << curr_vals[i];
    }
    cout << endl;
    cout.flush();

    vector<long long> r;  // responses
    r.reserve(n);
    long long r_prev;
    if (!(cin >> r_prev)) return 0;
    r.push_back(r_prev);

    // For candidate worlds: w = 0 -> op_n = '+', alpha = 1
    //                      w = 1 -> op_n = '*', alpha = z
    bool alive[2] = {true, true};
    vector<vector<int>> ops_world(2, vector<int>(n + 1, 0)); // store ops for 1..n-1
    long long Fprev[2] = {a0, a0}; // F_{t-1} for each world

    // Values assigned to positions 1..n-1 (final ones after their step)
    vector<long long> assigned(n + 1, 1);
    assigned[0] = a0;
    assigned[n] = z;

    // Collect A_t for potential debugging or future use (not strictly necessary)
    vector<long long> A(n + 1, 0);

    for (int t = 1; t <= n - 1; ++t) {
        // Choose v_t avoiding bad values for all alive worlds
        vector<long long> banned;
        banned.push_back(1); // we must have v_t != 1 (to keep denom != 0)

        for (int w = 0; w < 2; ++w) if (alive[w]) {
            long long u = Fprev[w] % MOD;
            if (u < 0) u += MOD;
            long long b1 = (1 - u + MOD) % MOD; // makes F_t = 1 if plus
            banned.push_back(b1);
            if (u != 0) {
                long long b2 = mod_inv(u);       // makes F_t = 1 if multiply
                banned.push_back(b2);
            }
        }

        long long v_t = 2;
        while (true) {
            bool ok = true;
            for (long long x : banned) {
                if (v_t == x) { ok = false; break; }
            }
            if (ok) break;
            ++v_t;
        }

        curr_vals[t] = v_t;
        assigned[t] = v_t;

        // Issue query t
        cout << "?";
        for (int i = 0; i <= n; ++i) {
            long long val;
            if (i == 0) val = a0;
            else if (i == n) val = z;
            else {
                if (i <= t) val = assigned[i];
                else val = 1;
            }
            cout << ' ' << val;
        }
        cout << endl;
        cout.flush();

        long long r_curr;
        if (!(cin >> r_curr)) return 0;
        r.push_back(r_curr);

        long long diff = (r_curr - r_prev + MOD) % MOD;
        long long denom = (v_t - 1 + MOD) % MOD;
        long long inv_denom = mod_inv(denom);
        long long At = diff * inv_denom % MOD;
        A[t] = At;

        // Update worlds
        for (int w = 0; w < 2; ++w) if (alive[w]) {
            long long alpha = (w == 0 ? 1LL : z) % MOD;
            long long u = Fprev[w] % MOD;
            if (u < 0) u += MOD;

            long long cand_plus = alpha;                  // op_t = '+'
            long long cand_mul  = alpha * u % MOD;        // op_t = '*'

            if (At == cand_plus) {
                ops_world[w][t] = 0; // '+'
                Fprev[w] = (u + v_t) % MOD;
            } else if (At == cand_mul) {
                ops_world[w][t] = 1; // '*'
                Fprev[w] = (u * v_t) % MOD;
            } else {
                alive[w] = false;
            }
        }

        r_prev = r_curr;
    }

    int selected_world = -1;

    for (int w = 0; w < 2; ++w) if (alive[w]) {
        bool ok = true;
        // Verify all queries for this world
        for (int k = 0; k < (int)r.size(); ++k) {
            vector<long long> x(n + 1);
            x[0] = a0;
            for (int i = 1; i <= n - 1; ++i) {
                if (i <= k) x[i] = assigned[i];
                else x[i] = 1;
            }
            x[n] = z;

            long long res = x[0] % MOD;
            for (int i = 1; i <= n - 1; ++i) {
                int op = ops_world[w][i];
                long long ai = x[i] % MOD;
                if (op == 0) res = (res + ai) % MOD;
                else res = (res * ai) % MOD;
            }
            int opn = (w == 0 ? 0 : 1); // last operator
            long long an = x[n] % MOD;
            if (opn == 0) res = (res + an) % MOD;
            else res = (res * an) % MOD;

            if (res != r[k]) {
                ok = false;
                break;
            }
        }
        if (ok) {
            selected_world = w;
            break;
        }
    }

    if (selected_world == -1) {
        // Fallback (should not happen); default to world 0
        selected_world = 0;
    }

    vector<int> final_ops(n + 1, 0);
    for (int i = 1; i <= n - 1; ++i) {
        final_ops[i] = ops_world[selected_world][i];
    }
    final_ops[n] = (selected_world == 0 ? 0 : 1);

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << final_ops[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}