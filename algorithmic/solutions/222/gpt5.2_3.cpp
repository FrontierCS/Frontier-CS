#include <bits/stdc++.h>
using namespace std;

static const int MAXV = 1'000'000;

struct Solver {
    vector<int> pos;
    vector<int> used;

    Solver() : pos(MAXV + 1, -1) {}

    int ask(int v, long long x) {
        cout << "? " << v << " " << x << endl; // endl flushes
        int res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    }

    void mark(int node, int j) {
        if (pos[node] == -1) used.push_back(node);
        pos[node] = j;
    }

    void cleanup() {
        for (int node : used) pos[node] = -1;
        used.clear();
    }

    static vector<int> factor_primes(int x) {
        vector<int> primes;
        for (int p = 2; 1LL * p * p <= x; ++p) {
            if (x % p == 0) {
                primes.push_back(p);
                while (x % p == 0) x /= p;
            }
        }
        if (x > 1) primes.push_back(x);
        return primes;
    }

    long long reduce_order(int c, long long cand) {
        long long ord = cand;
        vector<int> primes = factor_primes((int)ord);
        for (int p : primes) {
            while (ord % p == 0) {
                long long nxt = ord / p;
                int res = ask(c, nxt);
                if (res == c) ord = nxt;
                else break;
            }
        }
        return ord;
    }

    long long solve_one() {
        used.reserve(4096);

        int c = ask(1, 1);

        const int m = 1024;
        const int M = MAXV;
        const int maxI = (M + m - 1) / m;

        mark(c, 0);

        for (int j = 1; j <= m - 1; ++j) {
            int node = ask(c, j);
            if (node == c) {
                long long ans = j;
                cleanup();
                return ans;
            }
            mark(node, j);
        }

        long long cand = -1;
        for (int i = 1; i <= maxI; ++i) {
            long long x = 1LL * i * m;
            int node = ask(c, x);
            int j = pos[node];
            if (j != -1) {
                cand = x - j;
                break;
            }
        }

        if (cand == -1) cand = M; // fallback (should never happen)

        long long ans = reduce_order(c, cand);

        cleanup();
        return ans;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Solver solver;

    for (int tc = 0; tc < n; ++tc) {
        long long s = solver.solve_one();
        cout << "! " << s << endl;
        int verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == -1) return 0;
    }
    return 0;
}