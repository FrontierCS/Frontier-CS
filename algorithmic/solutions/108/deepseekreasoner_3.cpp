#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    int N = n * m;
    vector<int> rot(n, 0);
    int current_f;
    
    // initial query to get first f
    cout << "? 0 1" << endl;
    cin >> current_f;
    rot[0] = (rot[0] + 1) % N;
    
    while (current_f < N - m) {
        for (int i = 0; i < n; ++i) {
            bool improved = false;
            for (int dir : {1, -1}) {
                cout << "? " << i << " " << dir << endl;
                int new_f;
                cin >> new_f;
                rot[i] = (rot[i] + dir + N) % N;
                if (new_f > current_f) {
                    current_f = new_f;
                    improved = true;
                    // continue in this direction while it improves
                    while (true) {
                        cout << "? " << i << " " << dir << endl;
                        cin >> new_f;
                        rot[i] = (rot[i] + dir + N) % N;
                        if (new_f > current_f) {
                            current_f = new_f;
                        } else {
                            // revert last rotation
                            cout << "? " << i << " " << -dir << endl;
                            cin >> new_f; // should be previous current_f
                            rot[i] = (rot[i] - dir + N) % N;
                            current_f = new_f;
                            break;
                        }
                    }
                    break; // break out of dir loop
                } else {
                    // revert the trial rotation
                    cout << "? " << i << " " << -dir << endl;
                    cin >> new_f; // should be current_f
                    rot[i] = (rot[i] - dir + N) % N;
                }
            }
            if (improved) {
                // start from the first ring again to allow further improvements
                break;
            }
        }
    }
    
    // All rings are aligned, output zeros
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " 0";
    }
    cout << endl;
    
    return 0;
}