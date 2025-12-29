#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, T;
    cin >> N >> T;
    vector<string> board(N);
    for(int i = 0; i < N; i++) cin >> board[i];
    int ex = -1, ey = -1;
    for(int i = 0; i < N; i++) {
        for(int j = 0; j < N; j++) {
            if(board[i][j] == '0') {
                ex = i;
                ey = j;
            }
        }
    }
    string moves = "";
    int tx = N - 1, ty = N - 1;
    // Adjust column
    while(ey < ty) {
        moves += 'R';
        ey++;
    }
    while(ey > ty) {
        moves += 'L';
        ey--;
    }
    // Adjust row
    while(ex < tx) {
        moves += 'D';
        ex++;
    }
    while(ex > tx) {
        moves += 'U';
        ex--;
    }
    cout << moves << endl;
    return 0;
}