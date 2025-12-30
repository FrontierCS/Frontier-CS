#include <bits/stdc++.h>
using namespace std;

const int T = 15;

struct PairXY {
    short x = 0, y = 0;
};

unsigned char bitPos[1005][T];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << 1 << " " << 1 << '\n';
        cout.flush();
        return 0;
    }

    int pow3[T + 1];
    pow3[0] = 1;
    for (int i = 1; i <= T; ++i) pow3[i] = pow3[i - 1] * 3;
    int arr_size = pow3[T];

    vector<PairXY> arr(arr_size);

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    // Generate codes for positions with unique difference vectors
    for (int i = 1; i <= n; ++i) {
        while (true) {
            for (int k = 0; k < T; ++k) {
                bitPos[i][k] = (unsigned char)(rng() & 1);
            }
            bool ok = true;
            for (int j = 1; j < i && ok; ++j) {
                int idx1 = 0, idx2 = 0;
                for (int k = 0; k < T; ++k) {
                    int d1 = (int)bitPos[j][k] - (int)bitPos[i][k]; // s[j] - s[i] => (x=i,y=j)
                    int d2 = -d1;                                   // s[i] - s[j] => (x=j,y=i)
                    idx1 = idx1 * 3 + (d1 + 1);
                    idx2 = idx2 * 3 + (d2 + 1);
                }
                if (arr[idx1].x != 0 || arr[idx2].x != 0) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                for (int j = 1; j < i; ++j) {
                    int idx1 = 0, idx2 = 0;
                    for (int k = 0; k < T; ++k) {
                        int d1 = (int)bitPos[j][k] - (int)bitPos[i][k];
                        int d2 = -d1;
                        idx1 = idx1 * 3 + (d1 + 1);
                        idx2 = idx2 * 3 + (d2 + 1);
                    }
                    arr[idx1].x = (short)i; arr[idx1].y = (short)j; // D = s[j]-s[i] => (x=i,y=j)
                    arr[idx2].x = (short)j; arr[idx2].y = (short)i; // D = s[i]-s[j] => (x=j,y=i)
                }
                break;
            }
        }
    }

    vector<int> posVal(n + 1, -1);

    // Process values in pairs (a,b)
    for (int val = 1; val + 1 <= n; val += 2) {
        int a = val;
        int b = val + 1;
        int D[T];

        for (int k = 0; k < T; ++k) {
            cout << 0;
            for (int i = 1; i <= n; ++i) {
                int v = (bitPos[i][k] ? b : a);
                cout << ' ' << v;
            }
            cout << '\n';
            cout.flush();

            int score;
            if (!(cin >> score)) return 0;
            D[k] = score - 1; // D_k = s_k(pos[b]) - s_k(pos[a])
        }

        int key = 0;
        for (int k = 0; k < T; ++k) {
            key = key * 3 + (D[k] + 1);
        }
        PairXY pr = arr[key];
        int x = pr.x;
        int y = pr.y;
        posVal[a] = x;
        posVal[b] = y;
    }

    if (n % 2 == 1) {
        int last = n;
        vector<char> used(n + 1, 0);
        for (int v = 1; v <= n - 1; ++v) {
            if (posVal[v] >= 1 && posVal[v] <= n)
                used[posVal[v]] = 1;
        }
        int lastpos = 1;
        while (lastpos <= n && used[lastpos]) ++lastpos;
        if (lastpos > n) lastpos = 1;
        posVal[last] = lastpos;
    }

    vector<int> perm(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int pos = posVal[v];
        if (pos >= 1 && pos <= n) perm[pos] = v;
    }
    // Fallback (should not be needed)
    for (int i = 1; i <= n; ++i) if (perm[i] == 0) perm[i] = 1;

    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << perm[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}