#include <bits/stdc++.h>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int lo = 1, hi = 100000;
        while(lo < hi) {
            int mid = lo + (hi - lo + 1) / 2;
            cout << "? 1 " << mid << endl;
            cout.flush();
            int r;
            cin >> r;
            if(r == -1) return 0;
            if(r == 0) {
                hi = mid - 1;
            } else {
                lo = mid;
            }
        }
        cout << "! " << lo << endl;
        cout.flush();
    }
    return 0;
}