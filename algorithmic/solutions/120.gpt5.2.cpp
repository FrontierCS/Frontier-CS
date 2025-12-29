#include <bits/stdc++.h>
using namespace std;

static int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << "\n";
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r < 0) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 100;

    static int r[101][101];
    for (int i = 0; i <= 100; i++)
        for (int j = 0; j <= 100; j++)
            r[i][j] = -1;

    // Phase 1: query all pairs (i,j) among 2..100 with vertex 1
    for (int i = 2; i <= N; i++) {
        for (int j = i + 1; j <= N; j++) {
            r[i][j] = ask(1, i, j);
        }
    }

    auto getR = [&](int i, int j) -> int {
        if (i > j) swap(i, j);
        return r[i][j];
    };

    // Phase 2: query triangles among 2..100 to recover a[i] = edge(1,i)
    // For v >= 4: compute s23v = a2 + a3 + av using query (2,3,v)
    vector<int> s23(N + 1, -1);
    for (int v = 4; v <= N; v++) {
        int tri = ask(2, 3, v); // equals b23 + b2v + b3v
        int val = getR(2, 3) + getR(2, v) + getR(3, v) - tri;
        // val should be 2*(a2+a3+av)
        if (val % 2 != 0) exit(0);
        s23[v] = val / 2;
    }

    // Additional two triangle queries to determine a2 and a3 uniquely.
    int tri245 = ask(2, 4, 5);
    int val245 = getR(2, 4) + getR(2, 5) + getR(4, 5) - tri245;
    if (val245 % 2 != 0) exit(0);
    int s245 = val245 / 2; // a2+a4+a5

    int tri345 = ask(3, 4, 5);
    int val345 = getR(3, 4) + getR(3, 5) + getR(4, 5) - tri345;
    if (val345 % 2 != 0) exit(0);
    int s345 = val345 / 2; // a3+a4+a5

    vector<int> a(N + 1, 0); // a[i]=edge(1,i), a[1]=0

    bool found = false;
    for (int a2 = 0; a2 <= 1 && !found; a2++) {
        for (int a3 = 0; a3 <= 1 && !found; a3++) {
            // derive a4,a5 from s23[4], s23[5]
            int a4 = s23[4] - a2 - a3;
            int a5 = s23[5] - a2 - a3;
            if (a4 < 0 || a4 > 1 || a5 < 0 || a5 > 1) continue;

            if (a2 + a4 + a5 != s245) continue;
            if (a3 + a4 + a5 != s345) continue;

            vector<int> tmpa(N + 1, 0);
            tmpa[2] = a2;
            tmpa[3] = a3;
            bool ok = true;
            for (int v = 4; v <= N; v++) {
                int av = s23[v] - a2 - a3;
                if (av < 0 || av > 1) { ok = false; break; }
                tmpa[v] = av;
            }
            if (!ok) continue;

            // Validate all computed b_ij are 0/1
            for (int i = 2; i <= N && ok; i++) {
                for (int j = i + 1; j <= N; j++) {
                    int bij = getR(i, j) - tmpa[i] - tmpa[j];
                    if (bij != 0 && bij != 1) { ok = false; break; }
                }
            }
            if (!ok) continue;

            a = tmpa;
            found = true;
        }
    }
    if (!found) exit(0);

    vector<string> mat(N, string(N, '0'));
    for (int i = 1; i <= N; i++) {
        for (int j = i + 1; j <= N; j++) {
            int e = 0;
            if (i == 1) e = a[j];
            else if (j == 1) e = a[i];
            else e = getR(i, j) - a[i] - a[j];
            mat[i - 1][j - 1] = mat[j - 1][i - 1] = char('0' + e);
        }
    }

    cout << "!\n";
    for (int i = 0; i < N; i++) {
        cout << mat[i] << "\n";
    }
    cout.flush();
    return 0;
}