#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    auto ask = [&](int c)->char{
        cout << "? " << c << "\n";
        cout.flush();
        char ch;
        cin >> ch;
        return ch;
    };
    auto reset = [&](){
        cout << "R\n";
        cout.flush();
    };

    int L = 0;
    while ((1 << L) < n) L++;
    int mask = (1 << L) - 1;

    auto rotR = [&](int x, int p)->int{
        if (L == 0) return x;
        p %= L;
        int res = ((x >> p) | ((x << (L - p)) & mask)) & mask;
        return res;
    };

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    vector<char> bad(n, 0);

    for (int p = 0; p < L; ++p) {
        vector<pair<int,int>> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) {
            arr.emplace_back(rotR(i, p), i);
        }
        sort(arr.begin(), arr.end());
        for (int i = 0; i + 1 < n; i += 2) {
            int a = arr[i].second;
            int b = arr[i+1].second;
            reset();
            ask(a + 1); // this should always return 'N' due to reset
            char r = ask(b + 1);
            if (r == 'Y') bad[b] = 1;
        }
    }

    int d = 0;
    for (int i = 0; i < n; ++i) if (!bad[i]) d++;

    cout << "! " << d << "\n";
    cout.flush();
    return 0;
}