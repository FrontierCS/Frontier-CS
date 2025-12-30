#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 100;
    static long long T[101];
    static long long U[101][101];
    static long long deg[101];
    static int adj[101][101];

    long long L = 0; // sum over all triples

    for (int i = 1; i <= n - 2; ++i) {
        for (int j = i + 1; j <= n - 1; ++j) {
            for (int k = j + 1; k <= n; ++k) {
                cout << "? " << i << ' ' << j << ' ' << k << '\n' << flush;
                long long s;
                if (!(cin >> s)) {
                    return 0; // in case of interactor error
                }
                L += s;
                T[i] += s;
                T[j] += s;
                T[k] += s;
                U[i][j] += s;
                U[i][k] += s;
                U[j][k] += s;
            }
        }
    }

    long long E = L / (n - 2); // total number of edges

    for (int i = 1; i <= n; ++i) {
        deg[i] = (T[i] - E) / (n - 3);
    }

    for (int i = 1; i <= n; ++i) {
        adj[i][i] = 0;
    }

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            long long num = U[i][j] - deg[i] - deg[j];
            long long x = num / (n - 4); // should be 0 or 1
            adj[i][j] = adj[j][i] = (int)x;
        }
    }

    cout << "!\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << (adj[i][j] ? '1' : '0');
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}