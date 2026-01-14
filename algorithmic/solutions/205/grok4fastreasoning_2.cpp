#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    string s1, s2;
    cin >> s1 >> s2;
    auto get_k = [](const string& s) -> int {
        int bal = 0, k = 0;
        for (char c : s) {
            if (c == '(') bal++;
            else bal--;
            if (bal == 0) k++;
        }
        return k;
    };
    int k1 = get_k(s1);
    int k2 = get_k(s2);
    vector<pair<int, int>> ops;
    int len = 2 * n;
    if (k1 == k2) {
        cout << 0 << endl;
        return 0;
    }
    if (k2 == k1 + 1) {
        // increase by 1
        int i = -1;
        for (int j = len - 2; j >= 0; j--) {
            if (s1[j] == '(' && s1[j + 1] == ')') {
                i = j;
                break;
            }
        }
        if (i == -1) {
            cout << 0 << endl;
            return 0;
        }
        ops.emplace_back(6, i);
        ops.emplace_back(5, len - 2);
        cout << ops.size() << endl;
        for (auto [op, x] : ops) {
            cout << op << " " << x << endl;
        }
        return 0;
    }
    if (k1 <= k2) {
        cout << 0 << endl;
        return 0;
    }
    // k1 > k2
    int num_free = k1 - k2;
    if (k2 == 1) {
        num_free = k1 - 2;
        if (num_free < 0) num_free = 0;
    }
    for (int i = 0; i < num_free; i++) {
        ops.emplace_back(4, 0);
    }
    if (k2 == 1) {
        ops.emplace_back(5, len);
        ops.emplace_back(4, 0);
        ops.emplace_back(6, len);
    }
    cout << ops.size() << endl;
    for (auto [op, x] : ops) {
        cout << op << " " << x << endl;
    }
    return 0;
}