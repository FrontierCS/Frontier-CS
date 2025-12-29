#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<int> count(n, 0);
        vector<bool> active(n, true);
        int activeCount = n;
        
        while (activeCount > 2) {
            int idx = -1;
            for (int i = 0; i < n; i++) {
                if (active[i]) {
                    if (idx == -1 || count[i] < count[idx]) {
                        idx = i;
                    }
                }
            }
            cout << "0 " << idx << endl;
            int response;
            cin >> response;
            if (response == 1) {
                count[idx]++;
            } else {
                active[idx] = false;
                activeCount--;
            }
        }
        
        vector<int> remaining;
        for (int i = 0; i < n; i++) {
            if (active[i]) {
                remaining.push_back(i);
            }
        }
        cout << "1 " << remaining[0] << " " << remaining[1] << endl;
    }
    return 0;
}