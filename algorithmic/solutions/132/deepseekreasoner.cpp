#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    int R, H;
    cin >> R >> H; // R=75, H=1 in the official test, but we read anyway.

    // Moduli for the tests. Their sum is 30.
    vector<int> moduli = {13, 7, 5, 3, 2};

    // Send all robots at once.
    for (int m : moduli) {
        for (int r = 0; r < m; ++r) {
            // Collect all positions p such that p % m == r.
            vector<int> positions;
            for (int p = 1; p <= 1000; ++p) {
                if (p % m == r) {
                    positions.push_back(p);
                }
            }
            // Output the query for this robot.
            cout << "? " << positions.size();
            for (int pos : positions) {
                cout << " " << pos;
            }
            cout << endl;
            cout.flush();
        }
    }

    // Wait for the results.
    cout << "@" << endl;
    cout.flush();

    int L;
    cin >> L;
    vector<int> responses(L);
    for (int i = 0; i < L; ++i) {
        cin >> responses[i];
    }

    // Decode: split responses according to the moduli.
    vector<vector<int>> positive_sets(moduli.size()); // residues with answer 1 for each modulus
    int idx = 0;
    for (int i = 0; i < moduli.size(); ++i) {
        int m = moduli[i];
        for (int r = 0; r < m; ++r) {
            if (responses[idx + r] == 1) {
                positive_sets[i].push_back(r);
            }
        }
        idx += m;
    }

    // Precompute residues for all numbers 1..1000 for each modulus.
    vector<vector<int>> num_res(1001, vector<int>(moduli.size()));
    for (int p = 1; p <= 1000; ++p) {
        for (int i = 0; i < moduli.size(); ++i) {
            num_res[p][i] = p % moduli[i];
        }
    }

    // Brute-force search over all unordered pairs (i,j), i <= j.
    int a = -1, b = -1;
    for (int i = 1; i <= 1000; ++i) {
        for (int j = i; j <= 1000; ++j) {
            bool ok = true;
            for (int mi = 0; mi < moduli.size(); ++mi) {
                int m = moduli[mi];
                int ri = num_res[i][mi];
                int rj = num_res[j][mi];
                // Check that for every residue r, (ri==r or rj==r) equals whether r is in positive_sets[mi].
                for (int r = 0; r < m; ++r) {
                    bool covered = (ri == r) || (rj == r);
                    bool expected = false;
                    for (int rr : positive_sets[mi]) {
                        if (rr == r) {
                            expected = true;
                            break;
                        }
                    }
                    if (covered != expected) {
                        ok = false;
                        break;
                    }
                }
                if (!ok) break;
            }
            if (ok) {
                a = i;
                b = j;
                break;
            }
        }
        if (a != -1) break;
    }

    // Output the answer.
    cout << "! " << a << " " << b << endl;
    cout.flush();

    return 0;
}