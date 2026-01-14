#include <iostream>
#include <vector>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        int k = (n - 3) / 2; // integer division
        vector<bool> active(n, true);
        for (int round = 0; round < k; ++round) {
            for (int i = 0; i < n; ++i) {
                if (active[i]) {
                    cout << "0 " << i << endl;
                    int resp;
                    cin >> resp;
                    if (resp == 0) {
                        active[i] = false;
                    }
                }
            }
        }
        vector<int> alive;
        for (int i = 0; i < n; ++i) {
            if (active[i]) {
                alive.push_back(i);
            }
        }
        cout << "1 " << alive[0] << " " << alive[1] << endl;
    }
    return 0;
}