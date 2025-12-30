#include <iostream>
#include <vector>
#include <bitset>
#include <string>

using namespace std;

const int MAXN = 200;

int n;
bitset<MAXN> mask;

int query(const bitset<MAXN>& bs) {
    string s;
    for (int i = 0; i < n; ++i) {
        s += (bs[i] ? '1' : '0');
    }
    cout << "? " << s << endl;
    cout.flush();
    int ans;
    cin >> ans;
    return ans;
}

void solve() {
    cin >> n;
    vector<bool> inS(n, false);
    bitset<MAXN> S;
    int s_size = 0;

    // start from vertex 0
    S.set(0);
    inS[0] = true;
    s_size = 1;
    int qS = query(S);

    while (qS > 0) {
        vector<int> T;
        for (int i = 0; i < n; ++i) {
            if (!inS[i]) T.push_back(i);
        }

        int L = 0, R = (int)T.size() - 1;
        while (L < R) {
            int mid = (L + R) / 2;
            bitset<MAXN> X;
            for (int i = L; i <= mid; ++i) {
                X.set(T[i]);
            }
            int qX = query(X);
            bitset<MAXN> SUX = S | X;
            int qSUX = query(SUX);
            int F = qSUX - qX;
            if (F <= qS - 2) {
                R = mid;
            } else {
                L = mid + 1;
            }
        }

        int u = T[L];
        S.set(u);
        inS[u] = true;
        s_size++;
        qS = query(S);
    }

    if (s_size == n) {
        cout << "! 1" << endl;
    } else {
        cout << "! 0" << endl;
    }
    cout.flush();
}

int main() {
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}