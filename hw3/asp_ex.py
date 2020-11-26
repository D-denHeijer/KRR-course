import clingo


def print_answer_sets(program):
    # Load the answer set program, and call the grounder
    control = clingo.Control();
    control.add("base", [], program);
    control.ground([("base", [])]);
    # Define a function that will be called when an answer set is found
    # This function sorts the answer set alphabetically, and prints it
    def on_model(model):
        sorted_model = [str(atom) for atom in model.symbols(shown=True)];
        sorted_model.sort();
        print("Answer set: {{{}}}".format(", ".join(sorted_model)));
    # Ask clingo to find all models (using an upper bound of 0 gives all models)
    control.configuration.solve.models = 0;
    # Call the clingo solver, passing on the function on_model for when an answer set is found
    answer = control.solve(on_model=on_model)
    # Print a message when no answer set was found
    if answer.satisfiable == False:
        print("No answer sets");


print_answer_sets("""
    step(1..9).

    block(1..9).

    init(3,2). init(6,5). init(9,8).
    init(2,1). init(5,4). init(8,7).
    init(1,0). init(4,0). init(7,0).

    goal(8,6). goal(5,7).
    goal(6,4). goal(7,3).
    goal(4,2). goal(3,9).
    goal(2,1).

    location(0).
    location(B) :- block(B).
    { move(B,L,T) } :- block(B), location(L), step(T), B != L.
    object(B,T) :- move(B,_,T).
    target(B,T) :- move(_,B,T).
    :- step(T), 2 #count { object(B,T) : object(B,T) }.
    :- step(T), 2 #count { target(B,T) : target(B,T) }.

    on(B,L,0) :- init(B,L).
    on(B,L,T) :- move(B,L,T).
    on(B,L,T) :- on(B,L,T-1), step(T), not object(B,T).
    blocked(B,T) :- on(_,B,T), block(B), step(T+1).
    :- object(B,T), blocked(B,T -1).
    :- target(B,T), blocked(B,T -1).
    :- goal(B,L), step(T), not step(T+1), not on(B,L,T).
    #show move /3.
    """)

