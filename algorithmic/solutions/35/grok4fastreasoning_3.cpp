#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(0));
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int n;
        cin >> n;
        if(n == -1) return 0;
        int N = 2 * n - 1;
        vector<int> zero_count(n + 1, 0);
        for(int k = 0; k < 16; k++) {
            vector<int> S;
            for(int i = 1; i <= N; i++) {
                if(rand() % 2 == 0) S.push_back(i);
            }
            for(int x = 1; x <= n; x++) {
                cout << "? " << x << " " << S.size();
                for(int i : S) cout << " " << i;
                cout << "\n";
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) return 0;
                if(res == 0) zero_count[x]++;
            }
        }
        int max_zero = -1;
        int ans = -1;
        for(int x = 1; x <= n; x++) {
            if(zero_count[x] > max_zero) {
                max_zero = zero_count[x];
                ans = x;
            }
        }
        cout << "! " << ans << "\n";
        cout.flush();
    }
    return 0;
}