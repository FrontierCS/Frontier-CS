#include <bits/stdc++.h>
using namespace std;

struct Pet {
    int x, y, t;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<Pet> pets(N);
    for (int i = 0; i < N; i++) cin >> pets[i].x >> pets[i].y >> pets[i].t;

    int M;
    cin >> M;
    vector<pair<int,int>> humans(M);
    for (int i = 0; i < M; i++) cin >> humans[i].first >> humans[i].second;

    for (int turn = 0; turn < 300; turn++) {
        string actions(M, '.');
        cout << actions << "\n" << flush;

        vector<string> mv(N);
        for (int i = 0; i < N; i++) {
            if (!(cin >> mv[i])) return 0;
        }

        // Update pet positions (not needed for this trivial strategy, but harmless)
        for (int i = 0; i < N; i++) {
            for (char c : mv[i]) {
                if (c == '.') break;
                if (c == 'U') pets[i].x--;
                else if (c == 'D') pets[i].x++;
                else if (c == 'L') pets[i].y--;
                else if (c == 'R') pets[i].y++;
            }
        }
    }
    return 0;
}