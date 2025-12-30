#include <bits/stdc++.h>
using namespace std;

int cacheAns[101][101][101];

int ask(int a, int b, int c) {
    int arr[3] = {a, b, c};
    sort(arr, arr + 3);
    a = arr[0]; b = arr[1]; c = arr[2];
    int &res = cacheAns[a][b][c];
    if (res != -1) return res;
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    memset(cacheAns, -1, sizeof(cacheAns));

    const int N = 100;

    // Step 1: determine edges from vertex 1 to all others (2..100).
    // Unknowns: x[i] = edge(1, i) for i >= 2.

    int t123 = ask(1, 2, 3);

    // p[i] = parity of (x2 + x3 + xi) for i >= 4
    int p[101] = {0};

    for (int i = 4; i <= N; ++i) {
        int t12i = ask(1, 2, i);
        int t13i = ask(1, 3, i);
        int t23i = ask(2, 3, i);
        int s = (t123 + t12i + t13i - t23i) / 2; // x2 + x3 + xi
        p[i] = s & 1;
    }

    // q245 = parity of (x2 + x4 + x5)
    int s245 = (ask(1, 2, 4) + ask(1, 2, 5) + ask(1, 4, 5) - ask(2, 4, 5)) / 2;
    int q245 = s245 & 1;

    // q345 = parity of (x3 + x4 + x5)
    int s345 = (ask(1, 3, 4) + ask(1, 3, 5) + ask(1, 4, 5) - ask(3, 4, 5)) / 2;
    int q345 = s345 & 1;

    int x[101] = {0};  // x[i] = edge(1,i) for i>=2
    // Using relations:
    // x2 = q245 ^ p4 ^ p5
    // x3 = q345 ^ p4 ^ p5
    x[2] = q245 ^ p[4] ^ p[5];
    x[3] = q345 ^ p[4] ^ p[5];

    for (int i = 4; i <= N; ++i) {
        x[i] = p[i] ^ x[2] ^ x[3];
    }

    // Adjacency matrix
    static bool g[101][101];
    for (int i = 1; i <= N; ++i)
        for (int j = 1; j <= N; ++j)
            g[i][j] = false;

    // Fill edges from 1
    for (int i = 2; i <= N; ++i) {
        if (x[i]) {
            g[1][i] = g[i][1] = true;
        }
    }

    // Step 2: determine all edges among vertices 2..100 using triples (1, i, j)
    for (int i = 2; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            int t = ask(1, i, j); // t = x[i] + x[j] + edge(i,j)
            int eij = t - x[i] - x[j];
            if (eij) {
                g[i][j] = g[j][i] = true;
            }
        }
    }

    // Output the reconstructed graph
    cout << "!" << '\n';
    for (int i = 1; i <= N; ++i) {
        string s(N, '0');
        for (int j = 1; j <= N; ++j) {
            if (g[i][j]) s[j - 1] = '1';
        }
        cout << s << '\n';
    }
    cout.flush();

    return 0;
}