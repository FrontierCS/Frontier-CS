#include <bits/stdc++.h>
using namespace std;

static const int N = 100;

int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << "\n";
    cout.flush();
    int res;
    if (!(cin >> res)) {
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> adj(N + 1, vector<int>(N + 1, 0));
    vector<int> y(N + 1, 0); // y[i] = e_{1,i}
    vector<int> q13k(N + 1, -1), q1k2(N + 1, -1), q23k(N + 1, -1);
    int Q123 = ask(1, 2, 3);

    vector<int> S(N + 1, 0); // S[k] = y2 + y3 + yk for k>=4

    for (int k = 4; k <= N; ++k) {
        q13k[k] = ask(1, 3, k);
        q1k2[k] = ask(1, k, 2);
        q23k[k] = ask(2, 3, k);
        int sum = Q123 + q13k[k] + q1k2[k] - q23k[k];
        S[k] = sum / 2;
    }

    int q145 = ask(1, 4, 5);
    int q245 = ask(2, 4, 5);
    int q345 = ask(3, 4, 5);

    // Compute S_{2,4,5}
    int q124 = q1k2[4]; // ask(1,2,4)
    int q152 = q1k2[5]; // ask(1,5,2)
    int S245 = (q124 + q145 + q152 - q245) / 2;

    // Compute S_{3,4,5}
    int q134 = q13k[4]; // ask(1,3,4)
    int q153 = q13k[5]; // ask(1,3,5) same as ask(1,5,3)
    int S345 = (q134 + q145 + q153 - q345) / 2;

    int S4 = S[4], S5 = S[5];

    // T = y2 + y3
    int T = (2 * (S4 + S5) - (S245 + S345)) / 3;
    int D = S245 - S345; // y2 - y3

    int y2 = (T + D) / 2;
    int y3 = T - y2;
    y[2] = y2;
    y[3] = y3;

    for (int k = 4; k <= N; ++k) {
        y[k] = S[k] - T;
    }

    // Fill edges involving 1
    for (int j = 2; j <= N; ++j) {
        adj[1][j] = adj[j][1] = y[j];
    }

    // e23
    adj[2][3] = adj[3][2] = Q123 - y2 - y3;

    // e2k and e3k for k>=4
    for (int k = 4; k <= N; ++k) {
        int e2k = q1k2[k] - y2 - y[k];
        int e3k = q13k[k] - y3 - y[k];
        adj[2][k] = adj[k][2] = e2k;
        adj[3][k] = adj[k][3] = e3k;
    }

    // e45 from q145
    adj[4][5] = adj[5][4] = q145 - y[4] - y[5];

    // Compute remaining edges among 4..N (excluding 4,5 already known)
    for (int i = 4; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (i == 4 && j == 5) continue;
            int s = ask(1, i, j);
            int eij = s - y[i] - y[j];
            adj[i][j] = adj[j][i] = eij;
        }
    }

    cout << "!\n";
    for (int i = 1; i <= N; ++i) {
        string line;
        line.reserve(N);
        for (int j = 1; j <= N; ++j) {
            if (i == j) line.push_back('0');
            else line.push_back(adj[i][j] ? '1' : '0');
        }
        cout << line << "\n";
    }
    cout.flush();
    return 0;
}