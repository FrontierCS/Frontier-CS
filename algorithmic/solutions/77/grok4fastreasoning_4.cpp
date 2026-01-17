#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> mistakes(n, 0);
    for (int k = 0; k < m; k++) {
        string s;
        cin >> s;
        int min_mist = INT_MAX;
        for (int i = 0; i < n; i++) {
            min_mist = min(min_mist, mistakes[i]);
        }
        int count1 = 0, count0 = 0;
        for (int i = 0; i < n; i++) {
            if (mistakes[i] == min_mist) {
                if (s[i] == '1') count1++;
                else count0++;
            }
        }
        int pred = (count1 > count0) ? 1 : 0;
        cout << pred << endl;
        int outcome;
        cin >> outcome;
        for (int i = 0; i < n; i++) {
            int p_i = s[i] - '0';
            if (p_i != outcome) mistakes[i]++;
        }
    }
    return 0;
}