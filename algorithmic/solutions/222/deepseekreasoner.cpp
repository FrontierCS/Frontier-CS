#include <bits/stdc++.h>
using namespace std;

int query(int v, long long x) {
    cout << "? " << v << " " << x << endl;
    int res;
    cin >> res;
    return res;
}

void solve_one_graph() {
    const int B = 1000;
    unordered_map<int, int> idx;

    // Get a vertex on the cycle
    int c = query(1, 1);
    idx[c] = 0;

    // Baby steps
    long long m = -1;
    for (int i = 1; i < B; ++i) {
        int v = query(c, i);
        if (idx.find(v) != idx.end()) {
            m = i - idx[v];
            break;
        }
        idx[v] = i;
    }

    // Giant steps if needed
    if (m == -1) {
        int giant = query(c, B);
        long long j = 1;
        while (true) {
            if (idx.find(giant) != idx.end()) {
                int i = idx[giant];
                m = j * B - i;
                break;
            }
            giant = query(giant, B);
            ++j;
        }
    }

    // Reduce m to the true cycle length L
    long long L = m;
    bool changed;
    do {
        changed = false;
        for (long long p = 2; p * p <= L; ++p) {
            while (L % p == 0) {
                long long candidate = L / p;
                if (query(c, candidate) == c) {
                    L = candidate;
                    changed = true;
                } else {
                    break;
                }
            }
        }
    } while (changed);

    cout << "! " << L << endl;

    int verdict;
    cin >> verdict;
    if (verdict != 1) {
        exit(0);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    for (int i = 0; i < n; ++i) {
        solve_one_graph();
    }
    return 0;
}