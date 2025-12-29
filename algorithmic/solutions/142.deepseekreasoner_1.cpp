#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int n, m;
vector<int> stacks[52]; // poles 1..n+1
int cnt[52]; // number of balls on each pole
int correct_count[51]; // for poles 1..n, number of balls of correct color on that pole
bool complete[51]; // whether pole i is complete
int total_moves = 0;
const int BUFFER = 0; // will use index n+1 as buffer

// output a move and update data structures
void make_move(int from, int to) {
    int ball = stacks[from].back();
    stacks[from].pop_back();
    stacks[to].push_back();
    cnt[from]--;
    cnt[to]++;

    if (from <= n && ball == from) {
        correct_count[from]--;
    }
    if (to <= n && ball == to) {
        correct_count[to]++;
    }

    cout << from << " " << to << "\n";
    total_moves++;
}

// try to move the top ball of pole src to its target pole (color of that ball)
// returns true if a move was made
bool try_move_to_target(int src) {
    if (cnt[src] == 0) return false;
    int col = stacks[src].back();
    if (src == col) return false; // already on target

    int dst = col;

    if (cnt[dst] < m) {
        make_move(src, dst);
        return true;
    }

    // dst is full
    int d = stacks[dst].back();
    if (d == dst) {
        // dst full of correct balls, move src's ball to buffer
        if (cnt[n+1] < m) {
            make_move(src, n+1);
            return true;
        } else {
            // buffer full, try to free buffer
            if (try_move_to_target(n+1)) {
                make_move(src, n+1);
                return true;
            } else {
                // no recursive move possible, move a ball from buffer to any free pole
                for (int i = 1; i <= n+1; ++i) {
                    if (i != src && i != dst && cnt[i] < m) {
                        make_move(n+1, i);
                        make_move(src, n+1);
                        return true;
                    }
                }
                return false; // should not happen
            }
        }
    } else {
        // d != dst, try to move top ball of dst to its target
        if (try_move_to_target(dst)) {
            make_move(src, dst);
            return true;
        } else {
            // cannot move, move top ball of dst to buffer
            if (cnt[n+1] < m) {
                make_move(dst, n+1);
                make_move(src, dst);
                return true;
            } else {
                // buffer full, try to free buffer
                if (try_move_to_target(n+1)) {
                    make_move(dst, n+1);
                    make_move(src, dst);
                    return true;
                } else {
                    for (int i = 1; i <= n+1; ++i) {
                        if (i != src && i != dst && cnt[i] < m) {
                            make_move(n+1, i);
                            make_move(dst, n+1);
                            make_move(src, dst);
                            return true;
                        }
                    }
                    return false; // should not happen
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
        stacks[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> stacks[i][j];
        }
        // stack order: index 0 is bottom, m-1 is top
        reverse(stacks[i].begin(), stacks[i].end()); // now back() is top
        cnt[i] = m;
        // count correct balls on pole i
        correct_count[i] = 0;
        for (int ball : stacks[i]) {
            if (ball == i) correct_count[i]++;
        }
        complete[i] = false;
    }
    // buffer pole n+1
    stacks[n+1].clear();
    cnt[n+1] = 0;

    total_moves = 0;
    cout << "0\n"; // placeholder for number of moves, will be updated later

    // We'll store moves in a vector first, then output count and moves.
    // But the problem wants first line to be k, then moves. So we need to know k in advance.
    // Instead, we can output moves as we go, but then we need to print k first.
    // We'll collect moves in a vector and print at the end.

    vector<pair<int,int>> moves;
    // Temporarily redirect make_move to store moves
    // Override make_move to store in moves and update structures
    // Let's change make_move to store moves and also output later.
    // For now, we'll use a lambda to capture moves.

    auto make_move_lambda = [&](int from, int to) {
        int ball = stacks[from].back();
        stacks[from].pop_back();
        stacks[to].push_back(ball);
        cnt[from]--;
        cnt[to]++;

        if (from <= n && ball == from) {
            correct_count[from]--;
        }
        if (to <= n && ball == to) {
            correct_count[to]++;
        }

        moves.emplace_back(from, to);
        total_moves++;
    };

    // Replace make_move with the lambda in the functions? 
    // Since we already wrote functions using make_move, we need to adapt.
    // Let's rewrite the functions to use a function pointer or global variable? 
    // For simplicity, we'll copy the logic into main and use the lambda.
    // But that would be long. Instead, we'll use a global variable for moves vector.
    // We'll change make_move to use a global vector.

    // Let's redefine make_move as a macro that uses the moves vector.
    // But easier: We'll keep the functions but pass the moves vector as reference.
    // However, try_move_to_target calls itself recursively, so we need to pass the vector.
    // Let's restructure: We'll implement the algorithm in main without separate functions.

    // Given the complexity, we will implement a simpler greedy algorithm that is easier to control.

    // Alternative approach: repeatedly move misplaced top balls to their target, using buffer when needed.
    // We'll implement the main loop as described earlier, but using a custom move function that stores moves.

    // We'll create local functions inside main using lambdas.

    // Helper to check if a pole is complete
    auto is_complete = [&](int pole) -> bool {
        return correct_count[pole] == m && cnt[pole] == m;
    };

    // Custom move function
    auto my_move = [&](int from, int to) {
        int ball = stacks[from].back();
        stacks[from].pop_back();
        stacks[to].push_back(ball);
        cnt[from]--;
        cnt[to]++;

        if (from <= n && ball == from) {
            correct_count[from]--;
        }
        if (to <= n && ball == to) {
            correct_count[to]++;
        }

        moves.emplace_back(from, to);
    };

    // try_move_to_target adapted to use my_move
    function<bool(int)> try_move = [&](int src) -> bool {
        if (cnt[src] == 0) return false;
        int col = stacks[src].back();
        if (src == col) return false;

        int dst = col;
        if (cnt[dst] < m) {
            my_move(src, dst);
            return true;
        }

        // dst full
        int d = stacks[dst].back();
        if (d == dst) {
            if (cnt[n+1] < m) {
                my_move(src, n+1);
                return true;
            } else {
                if (try_move(n+1)) {
                    my_move(src, n+1);
                    return true;
                } else {
                    for (int i = 1; i <= n+1; ++i) {
                        if (i != src && i != dst && cnt[i] < m) {
                            my_move(n+1, i);
                            my_move(src, n+1);
                            return true;
                        }
                    }
                    return false;
                }
            }
        } else {
            if (try_move(dst)) {
                my_move(src, dst);
                return true;
            } else {
                if (cnt[n+1] < m) {
                    my_move(dst, n+1);
                    my_move(src, dst);
                    return true;
                } else {
                    if (try_move(n+1)) {
                        my_move(dst, n+1);
                        my_move(src, dst);
                        return true;
                    } else {
                        for (int i = 1; i <= n+1; ++i) {
                            if (i != src && i != dst && cnt[i] < m) {
                                my_move(n+1, i);
                                my_move(dst, n+1);
                                my_move(src, dst);
                                return true;
                            }
                        }
                        return false;
                    }
                }
            }
        }
    };

    // Main loop
    while (true) {
        bool moved = false;
        for (int i = 1; i <= n; ++i) {
            if (is_complete(i)) {
                complete[i] = true;
                continue;
            }
            while (cnt[i] > 0) {
                int col = stacks[i].back();
                if (col == i) {
                    if (is_complete(i)) {
                        complete[i] = true;
                        break;
                    }
                    // move correct ball away to expose below
                    int dest = -1;
                    if (cnt[n+1] < m) dest = n+1;
                    else {
                        for (int j = 1; j <= n+1; ++j) {
                            if (j != i && cnt[j] < m) {
                                dest = j;
                                break;
                            }
                        }
                    }
                    if (dest == -1) {
                        // try to create free space by moving a misplaced ball
                        for (int j = 1; j <= n; ++j) {
                            if (!complete[j] && cnt[j] > 0) {
                                int c = stacks[j].back();
                                if (c != j) {
                                    if (try_move(j)) {
                                        moved = true;
                                        break;
                                    }
                                }
                            }
                        }
                        // after that, try again to find dest
                        if (cnt[n+1] < m) dest = n+1;
                        else {
                            for (int j = 1; j <= n+1; ++j) {
                                if (j != i && cnt[j] < m) {
                                    dest = j;
                                    break;
                                }
                            }
                        }
                    }
                    if (dest != -1) {
                        my_move(i, dest);
                        moved = true;
                    } else {
                        // cannot proceed
                        break;
                    }
                } else {
                    if (try_move(i)) {
                        moved = true;
                    } else {
                        break;
                    }
                }
            }
        }

        // check if all complete
        bool all_complete = true;
        for (int i = 1; i <= n; ++i) {
            if (!is_complete(i)) {
                all_complete = false;
                break;
            }
        }
        if (all_complete) break;

        if (!moved) {
            // try to move a ball from buffer to any pole with space
            for (int i = 1; i <= n; ++i) {
                if (cnt[i] < m && cnt[n+1] > 0) {
                    my_move(n+1, i);
                    moved = true;
                    break;
                }
            }
            if (!moved) break;
        }
    }

    // Output
    cout << moves.size() << "\n";
    for (auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}