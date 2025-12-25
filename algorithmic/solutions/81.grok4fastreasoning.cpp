#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    assert(N == 1000);
    const int MAXQ = 1000;
    vector<bitset<1001>> mat(MAXQ);
    int qid = 0;
    for (int MM = 1; MM <= 51 && qid < MAXQ; ++MM) {
        for (int target_r = 0; target_r < MM && qid < MAXQ; ++target_r) {
            int m = 2 * MM;
            vector<int> aa(m), bb(m);
            for (int p = 0; p < MM; ++p) {
                for (int rr = 0; rr < 2; ++rr) {
                    int cur = p * 2 + rr;
                    // input 0
                    int new_p = (p + 1) % MM;
                    int new_rr = rr;
                    aa[cur] = new_p * 2 + new_rr;
                    // input 1
                    int delta = (p == target_r) ? 1 : 0;
                    new_rr = rr ^ delta;
                    bb[cur] = new_p * 2 + new_rr;
                }
            }
            cout << 1 << endl;
            cout << m << endl;
            for (int i = 0; i < m; ++i) {
                cout << aa[i];
                if (i < m - 1) cout << " ";
                else cout << endl;
            }
            for (int i = 0; i < m; ++i) {
                cout << bb[i];
                if (i < m - 1) cout << " ";
                else cout << endl;
            }
            cout.flush();
            int x;
            cin >> x;
            int val = x % 2;
            mat[qid][1000] = val;
            for (int i = 0; i < N; ++i) {
                if (i % MM == target_r) {
                    mat[qid][i] = 1;
                }
            }
            ++qid;
        }
    }
    // Gaussian elimination
    vector<int> pivot(N, -1);
    int rank = 0;
    for (int col = 0, roww = 0; col < N && roww < MAXQ; ++col) {
        int selected = -1;
        for (int i = roww; i < MAXQ; ++i) {
            if (mat[i][col]) {
                selected = i;
                break;
            }
        }
        if (selected == -1) continue;
        swap(mat[roww], mat[selected]);
        pivot[col] = roww;
        for (int i = 0; i < MAXQ; ++i) {
            if (i != roww && mat[i][col]) {
                mat[i] ^= mat[roww];
            }
        }
        ++roww;
        ++rank;
    }
    // Back substitution
    vector<int> s(N);
    for (int col = N - 1; col >= 0; --col) {
        int r = pivot[col];
        if (r == -1) {
            s[col] = 0; // arbitrary, but assume full rank
            continue;
        }
        int sum = mat[r][N];
        for (int higher = col + 1; higher < N; ++higher) {
            if (mat[r][higher]) {
                sum ^= s[higher];
            }
        }
        s[col] = sum;
    }
    // Output guess
    cout << 0 << endl;
    string ans = "";
    for (int i = 0; i < N; ++i) {
        ans += '0' + s[i];
    }
    cout << ans << endl;
    return 0;
}