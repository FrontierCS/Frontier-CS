#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int n;
        cin >> n;
        if(n == -1) exit(0);
        int N = 2 * n - 1;
        int found = -1;
        for(int x = 1; x <= n; x++) {
            // find first position
            int low = 1, high = N;
            while(low < high) {
                int mid = (low + high) / 2;
                cout << "? " << x << " " << mid;
                for(int j = 1; j <= mid; j++) {
                    cout << " " << j;
                }
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) exit(0);
                if(res == 1) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            }
            int p1 = low;
            // check for second
            bool has_second = false;
            if(p1 < N) {
                int sz = N - p1;
                cout << "? " << x << " " << sz;
                for(int j = p1 + 1; j <= N; j++) {
                    cout << " " << j;
                }
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if(res == -1) exit(0);
                if(res == 1) {
                    has_second = true;
                }
            }
            if(!has_second) {
                cout << "! " << x << endl;
                cout.flush();
                found = x;
                break;
            }
        }
        // if not found, error, but shouldn't happen
    }
    return 0;
}