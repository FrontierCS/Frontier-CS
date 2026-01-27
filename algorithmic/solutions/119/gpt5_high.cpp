#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

long long norm(long long x){
    x %= MOD;
    if(x < 0) x += MOD;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if(!(cin >> n)) return 0;

    auto ask = [&](const vector<long long>& a)->long long{
        cout << "?";
        for (long long v : a) cout << " " << v;
        cout << endl;
        cout.flush();
        long long res;
        if(!(cin >> res)) exit(0);
        return res;
    };

    vector<int> b(n+1, 0); // 0 for '+', 1 for '×', 1-indexed
    long long a0 = 2;

    // Query 1: determine b1 and total number of '+' (c_total)
    vector<long long> arr(n+1, 1);
    arr[0] = a0;
    arr[1] = n + 2; // ensure (a0-1)*(a1-1) > n
    for (int i = 2; i <= n; ++i) arr[i] = 1;
    long long r1 = ask(arr);

    long long candPlus = norm(r1 - ( (a0 + arr[1] - 1) % MOD ));
    long long candMul = norm(r1 - ( (a0 * arr[1]) % MOD ));

    long long c_total;
    if (candPlus <= n) { b[1] = 0; c_total = candPlus; }
    else { b[1] = 1; c_total = candMul; }

    // Subsequent queries: determine b[i] for i=2..n
    for (int i = 2; i <= n; ++i) {
        for (int j = 0; j <= n; ++j) arr[j] = 1;
        arr[0] = a0;
        arr[i] = 2;
        long long r = ask(arr);
        long long base = (c_total + (a0 + 2 - 1)) % MOD; // c_total + a0 + ai - 1, with ai=2
        long long D = norm(r - base);
        if (D == 0) b[i] = 0; // plus
        else b[i] = 1; // multiply
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << b[i];
    cout << endl;
    cout.flush();

    return 0;
}