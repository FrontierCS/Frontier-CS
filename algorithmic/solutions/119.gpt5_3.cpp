#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

long long ask(const vector<long long>& a) {
    cout << "?";
    for (auto v : a) {
        cout << " " << v;
    }
    cout << endl;
    cout.flush();
    long long res;
    if (!(cin >> res)) {
        exit(0);
    }
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        // Single query: a0=2, a1=1 -> result is 3 if plus, 2 if multiply
        vector<long long> a(2, 1);
        a[0] = 2; a[1] = 1;
        long long res = ask(a);
        int op = (res == 3 ? 0 : 1); // 0 for '+', 1 for '*'
        cout << "! " << op << endl;
        cout.flush();
        return 0;
    }

    vector<long long> R(n + 1, 0); // 1-indexed for convenience

    // Special query for i=1: a0=3, a1=2, others=1
    {
        vector<long long> a(n + 1, 1);
        a[0] = 3;
        a[1] = 2;
        R[1] = ask(a);
    }

    // Queries for i=2..n: a0=2, ai=2, others=1
    for (int i = 2; i <= n; ++i) {
        vector<long long> a(n + 1, 1);
        a[0] = 2;
        a[i] = 2;
        R[i] = ask(a);
    }

    // Determine min among i>=2
    long long minR2 = R[2];
    for (int i = 3; i <= n; ++i) minR2 = min(minR2, R[i]);

    // Determine if there is at least one plus among i>=2 and op1
    long long diff = R[1] - minR2; // This will be small and within [-1,3]
    bool plus_in_2_to_n = (diff == 1 || diff == 3);

    vector<int> op(n + 1, 1); // default multiply (1), 0 for '+'
    // Classify i>=2
    if (plus_in_2_to_n) {
        for (int i = 2; i <= n; ++i) {
            if (R[i] == minR2) op[i] = 0; // '+'
            else op[i] = 1; // '*'
        }
    } else {
        for (int i = 2; i <= n; ++i) op[i] = 1; // all '*'
    }

    // Classify i=1 using diff
    if (plus_in_2_to_n) {
        // diff == 1 -> plus, diff == 3 -> multiply
        op[1] = (diff == 1 ? 0 : 1);
    } else {
        // diff == -1 -> plus, diff == 2 -> multiply
        op[1] = (diff == -1 ? 0 : 1);
    }

    cout << "!" ;
    for (int i = 1; i <= n; ++i) {
        cout << " " << op[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}