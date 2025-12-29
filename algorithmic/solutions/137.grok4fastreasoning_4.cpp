#include <bits/stdc++.h>
using namespace std;

int main() {
    cout << 20 << " " << 20 << endl;
    for(int i = 0; i < 20; i++) {
        for(int j = 0; j < 20; j++) {
            if(i == 9 || j == 9) {
                cout << '1';
            } else {
                cout << '0';
            }
        }
        cout << endl;
    }
    return 0;
}