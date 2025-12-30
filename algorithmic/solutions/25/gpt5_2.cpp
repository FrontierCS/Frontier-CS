#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct RNG {
    uint64_t seed;
    RNG() {
        uint64_t x = chrono::high_resolution_clock::now().time_since_epoch().count();
        seed = splitmix64(x);
    }
    uint64_t next() { return seed = splitmix64(seed); }
    int uniform_int(int l, int r) { return l + (int)(next() % (uint64_t)(r - l + 1)); }
    double uniform_double() { return (next() >> 11) * (1.0 / (1ULL << 53)); }
    template<class It>
    void shuffle(It first, It last) {
        int n = (int)distance(first, last);
        if (n <= 1) return;
        for (int i = n - 1; i > 0; --i) {
            int j = uniform_int(0, i);
            iter_swap(first + i, first + j);
        }
    }
};

struct Solver {
    int T;
    int n;
    RNG rng;
    int queries_used;
    const int QUERY_LIMIT = 3500;

    int query(const vector<int>& bits) {
        string s; s.reserve(n);
        for (int i = 0; i < n; ++i) s.push_back(bits[i] ? '1' : '0');
        cout << "? " << s << endl << flush;
        int ans;
        if (!(cin >> ans)) exit(0);
        queries_used++;
        return ans;
    }

    int boundary_count(const vector<int>& bits) {
        int a = query(bits);
        vector<int> comp(n);
        for (int i = 0; i < n; ++i) comp[i] = bits[i] ? 0 : 1;
        int b = query(comp);
        return a + b;
    }

    bool try_local_search(int passes, int budget_per_restart, int& bfound) {
        // Initialize random nontrivial S
        vector<int> S(n, 0);
        int ones = 0;
        for (;;) {
            ones = 0;
            for (int i = 0; i < n; ++i) {
                S[i] = rng.uniform_int(0, 1);
                ones += S[i];
            }
            if (ones > 0 && ones < n) break;
        }
        int b = boundary_count(S);
        if (b == 0) { bfound = b; return true; }

        vector<int> order(n);
        iota(order.begin(), order.end(), 0);

        for (int pass = 0; pass < passes; ++pass) {
            rng.shuffle(order.begin(), order.end());
            bool improved = false;

            for (int idx = 0; idx < n; ++idx) {
                if (queries_used + 2 > QUERY_LIMIT) break;
                int i = order[idx];
                S[i] ^= 1;
                int cnt = 0;
                for (int j = 0; j < n; ++j) cnt += S[j];
                if (cnt == 0 || cnt == n) {
                    S[i] ^= 1;
                    continue;
                }
                int b2 = boundary_count(S);
                if (b2 < b) {
                    b = b2;
                    improved = true;
                    if (b == 0) { bfound = b; return true; }
                } else {
                    S[i] ^= 1;
                }
                if (queries_used >= budget_per_restart) break;
            }
            if (!improved) break;
            if (queries_used >= budget_per_restart) break;
        }
        bfound = b;
        return (b == 0);
    }

    void solve_case() {
        queries_used = 0;
        if (!(cin >> n)) exit(0);

        if (n <= 1) {
            cout << "! 1" << endl << flush;
            return;
        }

        // Quick check for isolated vertex
        vector<int> singleton(n, 0);
        bool disconnected = false;
        for (int i = 0; i < n; ++i) {
            if (queries_used >= QUERY_LIMIT) break;
            fill(singleton.begin(), singleton.end(), 0);
            singleton[i] = 1;
            int d = query(singleton);
            if (d == 0 && n > 1) {
                disconnected = true;
                break;
            }
        }
        if (disconnected) {
            cout << "! 0" << endl << flush;
            return;
        }

        // Heuristic local search to find a cut with zero boundary
        int max_restarts = 4;
        int passes = 2;

        // Budget management: leave some headroom
        int remaining_budget = QUERY_LIMIT - queries_used - 10;
        if (remaining_budget < 0) remaining_budget = 0;

        int budget_per_restart = remaining_budget / max(1, max_restarts);

        for (int r = 0; r < max_restarts && queries_used < QUERY_LIMIT; ++r) {
            int bfound = -1;
            bool ok = try_local_search(passes, queries_used + budget_per_restart, bfound);
            if (ok) {
                cout << "! 0" << endl << flush;
                return;
            }
        }

        // If no evidence of disconnection found, assume connected
        cout << "! 1" << endl << flush;
    }

    void run() {
        if (!(cin >> T)) exit(0);
        for (int tc = 0; tc < T; ++tc) {
            solve_case();
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Solver s;
    s.run();
    return 0;
}