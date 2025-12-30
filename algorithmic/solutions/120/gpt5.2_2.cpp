#include <bits/stdc++.h>
using namespace std;

static int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << "\n" << flush;
    int r;
    if (!(cin >> r)) exit(0);
    if (r < 0) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 100;

    static int q1[101][101];
    static int q2[101][101];
    static int q12[101];

    for (int i = 1; i <= N; i++) {
        q12[i] = -1;
        for (int j = 1; j <= N; j++) q1[i][j] = q2[i][j] = -1;
    }

    // Queries:
    // For all 3 <= i < j <= 100:
    //   q1[i][j] = edges among {1,i,j} = e(1,i)+e(1,j)+e(i,j)
    //   q2[i][j] = edges among {2,i,j} = e(2,i)+e(2,j)+e(i,j)
    for (int i = 3; i <= N; i++) {
        for (int j = i + 1; j <= N; j++) {
            q1[i][j] = ask(1, i, j);
        }
    }
    for (int i = 3; i <= N; i++) {
        for (int j = i + 1; j <= N; j++) {
            q2[i][j] = ask(2, i, j);
        }
    }

    // For all i = 3..100:
    // q12[i] = edges among {1,2,i} = e12 + e(1,i) + e(2,i)
    for (int i = 3; i <= N; i++) {
        q12[i] = ask(1, 2, i);
    }

    // Solve.
    // Let A[i]=e(1,i), i>=2
    // Let B[i]=e(2,i), i>=3, and B[1]=e12
    // Let D[i]=A[i]-B[i], i>=3, in {-1,0,1}
    // diff[i][j]=q1-q2=D[i]+D[j]
    static int D[101];
    static int A[101];
    static int B[101];
    static int E[101][101];

    auto getDiff = [&](int i, int j) -> int {
        if (i > j) swap(i, j);
        return q1[i][j] - q2[i][j];
    };

    bool found = false;
    int e12_ans = -1;

    for (int d3 = -1; d3 <= 1 && !found; d3++) {
        bool ok = true;
        for (int i = 1; i <= N; i++) D[i] = 0;
        D[3] = d3;

        for (int v = 4; v <= N; v++) {
            int diff3v = getDiff(3, v);
            D[v] = diff3v - d3;
            if (D[v] < -1 || D[v] > 1) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        for (int i = 3; i <= N && ok; i++) {
            for (int j = i + 1; j <= N; j++) {
                if (D[i] + D[j] != getDiff(i, j)) {
                    ok = false;
                    break;
                }
            }
        }
        if (!ok) continue;

        for (int e12 = 0; e12 <= 1 && !found; e12++) {
            for (int i = 1; i <= N; i++) {
                A[i] = B[i] = 0;
                for (int j = 1; j <= N; j++) E[i][j] = 0;
            }
            A[2] = e12;
            B[1] = e12;

            bool ok2 = true;
            for (int i = 3; i <= N; i++) {
                int s = q12[i] - e12; // A[i] + B[i]
                if (s < 0 || s > 2) { ok2 = false; break; }
                if (((s + D[i]) & 1) != 0) { ok2 = false; break; }
                int ai = (s + D[i]) / 2;
                int bi = (s - D[i]) / 2;
                if (ai < 0 || ai > 1 || bi < 0 || bi > 1) { ok2 = false; break; }
                A[i] = ai;
                B[i] = bi;
            }
            if (!ok2) continue;

            for (int i = 3; i <= N && ok2; i++) {
                for (int j = i + 1; j <= N; j++) {
                    int e = q1[i][j] - A[i] - A[j];
                    if (e != 0 && e != 1) { ok2 = false; break; }
                    int e2 = q2[i][j] - B[i] - B[j];
                    if (e2 != e) { ok2 = false; break; }
                    E[i][j] = E[j][i] = e;
                }
            }
            if (!ok2) continue;

            e12_ans = e12;
            found = true;
        }
    }

    if (!found) {
        // Should never happen for a consistent interactor.
        exit(0);
    }

    static unsigned char adj[101][101];
    for (int i = 1; i <= N; i++) for (int j = 1; j <= N; j++) adj[i][j] = 0;

    adj[1][2] = adj[2][1] = (unsigned char)e12_ans;

    for (int i = 3; i <= N; i++) {
        adj[1][i] = adj[i][1] = (unsigned char)A[i];
        adj[2][i] = adj[i][2] = (unsigned char)B[i];
    }
    for (int i = 3; i <= N; i++) {
        for (int j = i + 1; j <= N; j++) {
            adj[i][j] = adj[j][i] = (unsigned char)E[i][j];
        }
    }

    cout << "!\n";
    for (int i = 1; i <= N; i++) {
        string s;
        s.reserve(N);
        for (int j = 1; j <= N; j++) {
            if (i == j) s.push_back('0');
            else s.push_back(adj[i][j] ? '1' : '0');
        }
        cout << s << "\n";
    }
    cout << flush;

    return 0;
}