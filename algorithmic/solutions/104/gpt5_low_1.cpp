#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--) {
        int n;
        if(!(cin >> n)) return 0;

        int l = 1, r = n;
        int last_guess = -1;
        while(l < r) {
            int mid = (l + r) / 2;
            cout << "? " << l << " " << mid << "\n";
            cout.flush();
            int x;
            if(!(cin >> x)) return 0;
            int len = mid - l + 1;
            // Assume honest: x == len if absent not in [l,mid], x == len-1 if absent in [l,mid]
            if (x == len - 1) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        last_guess = l;
        cout << "! " << last_guess << "\n";
        cout.flush();
        int y;
        if(!(cin >> y)) return 0;
        if(y == 0) {
            // If wrong, make a second arbitrary guess (fallback)
            int alt = (last_guess == 1 ? 2 : 1);
            cout << "! " << alt << "\n";
            cout.flush();
            if(!(cin >> y)) return 0;
        }
        cout << "#\n";
        cout.flush();
    }
    return 0;
}