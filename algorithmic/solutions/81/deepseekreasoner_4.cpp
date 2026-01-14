#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int N;
    cin >> N; // N = 1000
    string S(N, '0');
    
    for (int i = 0; i < N; ++i) {
        int m = i + 3;
        cout << "1" << endl; // indicate query
        cout << m;
        // output sequence a
        for (int j = 0; j < m; ++j) {
            if (j == 0 || j == 1) {
                cout << " " << j; // a[j] = j
            } else if (j <= i + 1) {
                cout << " " << j + 1; // a[j] = j+1
            } else { // j == i+2
                cout << " " << 0; // a[i+2] = 0
            }
        }
        // output sequence b
        for (int j = 0; j < m; ++j) {
            if (j == 0 || j == 1) {
                cout << " " << j; // b[j] = j
            } else if (j <= i + 1) {
                cout << " " << j + 1; // b[j] = j+1
            } else { // j == i+2
                cout << " " << 1; // b[i+2] = 1
            }
        }
        cout << endl;
        cout.flush();
        
        int res;
        cin >> res;
        S[i] = (res == 0 ? '0' : '1');
    }
    
    cout << "0" << endl;
    cout << S << endl;
    cout.flush();
    
    return 0;
}