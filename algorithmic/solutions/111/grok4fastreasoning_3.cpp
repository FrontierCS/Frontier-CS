#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int req = (int)floor(sqrt((double)n / 2.0));
    if (req == 0) req = 1;
    vector<int> S;
    const int MAX_XOR = 1 << 24;
    vector<char> usd(MAX_XOR, 0);
    for (int cand = 1; cand <= n && (int)S.size() < req; ++cand) {
        bool can = true;
        vector<int> news;
        for (int s : S) {
            int xv = cand ^ s;
            if (xv >= MAX_XOR || usd[xv]) {
                can = false;
                break;
            }
            news.push_back(xv);
        }
        if (can) {
            for (int v : news) {
                usd[v] = 1;
            }
            S.push_back(cand);
        }
    }
    cout << S.size() << endl;
    for (size_t i = 0; i < S.size(); ++i) {
        cout << S[i];
        if (i + 1 < S.size()) cout << " ";
    }
    cout << endl;
    return 0;
}