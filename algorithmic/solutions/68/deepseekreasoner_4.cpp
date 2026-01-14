#include <iostream>
#include <vector>
using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        // Query each pen once
        vector<int> alive;
        for (int i = 0; i < n; ++i) {
            cout << "0 " << i << endl;
            int resp;
            cin >> resp;
            if (resp == 1) {
                alive.push_back(i);
            }
        }
        // Simply pick the first two pens that responded with 1
        // (This is a placeholder – not guaranteed to be correct)
        int a = alive[0];
        int b = alive[1];
        cout << "1 " << a << " " << b << endl;
    }
    return 0;
}