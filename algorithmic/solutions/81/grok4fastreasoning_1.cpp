#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    string S = "";
    for (int pos = 0; pos < N; pos++) {
        int k = pos;
        int mm = k + 3;
        vector<int> aa(mm);
        vector<int> bb(mm);
        for (int x = 0; x < mm; x++) {
            aa[x] = x;
            bb[x] = x;
        }
        for (int j = 0; j < k; j++) {
            int st = j;
            int inp = S[j] - '0';
            int nxt = j + 1;
            if (inp == 0) {
                aa[st] = nxt;
            } else {
                bb[st] = nxt;
            }
        }
        int B = k;
        int os = k + 1;
        int iss = k + 2;
        aa[B] = os;
        bb[B] = iss;
        aa[os] = os;
        bb[os] = os;
        aa[iss] = iss;
        bb[iss] = iss;
        cout << 1 << endl;
        cout << mm;
        for (int x = 0; x < mm; x++) {
            cout << " " << aa[x];
        }
        cout << endl;
        for (int x = 0; x < mm; x++) {
            cout << " " << bb[x];
        }
        cout << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == os) {
            S += '0';
        } else {
            S += '1';
        }
    }
    cout << 0 << endl;
    cout << S << endl;
    cout.flush();
    return 0;
}