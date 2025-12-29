#include <bits/stdc++.h>
using namespace std;

static int ask(const string& q) {
    cout << q << flush;
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static string buildRepeatedQuery(int n, int val) {
    string s;
    s.reserve(32 + (size_t)n * 6);
    s += "? ";
    s += to_string(n);
    for (int i = 0; i < n; i++) {
        s.push_back(' ');
        s += to_string(val);
    }
    s.push_back('\n');
    return s;
}

static string buildSecondQueryBig(int L) {
    // n = 631, article: [L,1,L,2,...,L,315,L]
    const int n = 631;
    string s;
    s.reserve(32 + (size_t)n * 7);
    s += "? ";
    s += to_string(n);
    s.push_back(' ');
    s += to_string(L);
    for (int i = 1; i <= 315; i++) {
        s.push_back(' ');
        s += to_string(i);
        s.push_back(' ');
        s += to_string(L);
    }
    s.push_back('\n');
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    const int K = 316;
    const int N1 = 100000;
    const int Nsmall = 100000;

    vector<int> invC(N1 + 1, -1);
    for (int c = 1; c <= 316; c++) {
        int lines = (N1 + c - 1) / c;
        invC[lines] = c;
    }

    vector<int> invWsmall(Nsmall + 1, -1);
    for (int w = 1; w <= 315; w++) {
        int lines = (Nsmall + w - 1) / w;
        invWsmall[lines] = w;
    }

    const string q1 = buildRepeatedQuery(N1, K);
    const string qSmall = buildRepeatedQuery(Nsmall, 1);

    while (t--) {
        int res1 = ask(q1);
        if (res1 == 0) {
            int res2 = ask(qSmall);
            int W = (res2 >= 0 && res2 <= Nsmall) ? invWsmall[res2] : -1;
            if (W == -1) exit(0);
            cout << "! " << W << '\n' << flush;
        } else {
            int c = (res1 >= 0 && res1 <= N1) ? invC[res1] : -1;
            if (c == -1) exit(0);
            int L = K * c;
            string q2 = buildSecondQueryBig(L);
            int res2 = ask(q2);
            int W = L + (631 - res2);
            cout << "! " << W << '\n' << flush;
        }
    }
    return 0;
}