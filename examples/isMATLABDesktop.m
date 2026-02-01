function tf = isMATLABDesktop

    import matlab.internal.capability.Capability;
    isMO = Capability.isSupported(Capability.LocalClient);

    if isMO
        tf = true;
    else

        tf = false;
    end

end