#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> mem;

int ask(int i, int j) {
    if (i == j) return -1;
    int idx1 = i * n + j;
    if (mem[idx1] != -1) return mem[idx1];
    cout << "? " << i + 1 << " " << j + 1 << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    mem[idx1] = x;
    mem[j * n + i] = x;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;
    mem.assign(n * n, -1);

    // Initialize two random distinct indices
    mt19937 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());
    int a = uniform_int_distribution<int>(0, n - 1)(rng);
    int b = uniform_int_distribution<int>(0, n - 1)(rng);
    while (b == a) b = uniform_int_distribution<int>(0, n - 1)(rng);

    vector<int> ord;
    ord.reserve(n - 2);
    for (int i = 0; i < n; ++i) if (i != a && i != b) ord.push_back(i);
    shuffle(ord.begin(), ord.end(), rng);

    for (int i : ord) {
        int A = ask(a, i);
        int B = ask(b, i);
        if (A < B) {
            b = i;
        } else if (B < A) {
            a = i;
        } else {
            // do nothing
        }
    }

    // Now one of a or b is zero. Identify which.
    int z = -1;
    vector<int> others;
    others.reserve(n - 2);
    for (int i = 0; i < n; ++i) if (i != a && i != b) others.push_back(i);
    shuffle(others.begin(), others.end(), rng);

    for (int j : others) {
        int A = ask(a, j);
        int B = ask(b, j);
        if (A < B) { z = a; break; }
        if (B < A) { z = b; break; }
    }
    if (z == -1) {
        // fallback: try some more randoms including a/b swap attempts
        for (int rep = 0; rep < 100 && z == -1; ++rep) {
            int j = uniform_int_distribution<int>(0, n - 1)(rng);
            if (j == a || j == b) continue;
            int A = ask(a, j);
            int B = ask(b, j);
            if (A < B) { z = a; break; }
            if (B < A) { z = b; break; }
        }
        if (z == -1) z = a; // as a last resort
    }

    vector<int> p(n, -1);
    p[z] = 0;
    for (int i = 0; i < n; ++i) {
        if (i == z) continue;
        p[i] = ask(z, i);
    }

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << p[i] << (i + 1 == n ? '\n' : ' ');
    }
    cout.flush();
    return 0;
}